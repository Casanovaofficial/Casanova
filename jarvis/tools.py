"""Everything Jarvis can physically do on the computer.
Add a new ability = add a method decorated with @tool. The model sees it automatically."""
import datetime
import fnmatch
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

log = logging.getLogger("jarvis.tools")
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
NO_WINDOW = 0x08000000 if IS_WIN else 0

DANGEROUS = re.compile(
    r"\b(rm|rmdir|del|erase|format|mkfs|diskpart|shutdown|restart-computer|stop-computer|"
    r"remove-item|reg\s+delete|taskkill|kill|pkill|dd|chmod|chown|sudo|bcdedit|cipher)\b", re.I)


def tool(description, **params):
    """params: name=(json_type, description, required)"""
    def wrap(fn):
        props, required = {}, []
        for p, (typ, desc, req) in params.items():
            props[p] = {"type": typ, "description": desc}
            if req:
                required.append(p)
        fn._tool_spec = {"type": "function", "function": {
            "name": fn.__name__, "description": description,
            "parameters": {"type": "object", "properties": props, "required": required}}}
        return fn
    return wrap


class Toolbox:
    def __init__(self, cfg, confirm, memory, on_tool=None, on_reload=None):
        self.cfg, self.confirm, self.memory = cfg, confirm, memory
        self.on_tool = on_tool          # optional callback so the GUI can show activity
        self.on_reload = on_reload      # called after Jarvis changes its own settings
        roots = cfg["safety"].get("allowed_roots") or [str(Path.home())]
        self.roots = [self._path(r) for r in roots]
        self._registry = {}
        for name in dir(self):
            fn = getattr(self, name)
            spec = getattr(fn, "_tool_spec", None)
            if spec:
                self._registry[spec["function"]["name"]] = fn

    # ── plumbing ──────────────────────────────────
    def schemas(self):
        return [fn._tool_spec for fn in self._registry.values()]

    def run(self, name, args):
        fn = self._registry.get(name)
        if not fn:
            return f"Error: unknown tool '{name}'."
        try:
            log.info("TOOL %s %s", name, args)
            if self.on_tool:
                try:
                    self.on_tool(name, args)
                except Exception:
                    pass
            return str(fn(**(args or {})))
        except Exception as e:
            log.exception("Tool %s failed", name)
            return f"Error: {type(e).__name__}: {e}"

    def _ok(self, question):
        return (not self.cfg["safety"].get("confirm_dangerous", True)) or self.confirm(question)

    @staticmethod
    def _path(p):
        path = Path(os.path.expandvars(os.path.expanduser(str(p or "~"))))
        if not path.is_absolute():
            path = Path.home() / path
        return path.resolve()

    def _writable(self, path: Path):
        return any(path == r or r in path.parents for r in self.roots)

    # ── system / shell ────────────────────────────
    @tool("Run a shell command (PowerShell on Windows, bash on Mac/Linux) and return its output. "
          "Use for anything without a dedicated tool.",
          command=("string", "The exact command", True),
          timeout=("integer", "Seconds before giving up (default 60)", False))
    def run_command(self, command, timeout=60):
        if DANGEROUS.search(command) and not self._ok(f"Confirm, should I run: {command}? Yes or no."):
            return "Cancelled by user."
        args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command] if IS_WIN else ["bash", "-lc", command]
        p = subprocess.run(args, capture_output=True, text=True, timeout=int(timeout),
                           cwd=str(Path.home()), creationflags=NO_WINDOW)
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        return f"exit={p.returncode}\n{out[-3500:]}" if out else f"exit={p.returncode} (no output)"

    @tool("Get CPU, RAM, disk and battery status.")
    def system_status(self):
        disk = psutil.disk_usage(str(Path.home().anchor or "/"))
        bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        b = f", battery {bat.percent:.0f}% {'charging' if bat.power_plugged else 'on battery'}" if bat else ""
        return (f"CPU {psutil.cpu_percent(interval=0.5)}%, RAM {psutil.virtual_memory().percent}%, "
                f"disk {disk.percent}% used ({disk.free // 2**30} GB free){b}")

    @tool("Get the current local date and time.")
    def get_datetime(self):
        return datetime.datetime.now().strftime("%A %Y-%m-%d %H:%M")

    @tool("See what the user is doing right now: the window in front, their other open "
          "windows, and the clipboard. Use this to resolve 'this', 'that' or 'here'.")
    def get_context(self):
        import context
        return context.describe()

    @tool("List running processes, optionally filtered by name.",
          filter=("string", "Part of the process name", False))
    def list_processes(self, filter=""):
        procs = sorted({p.info["name"] for p in psutil.process_iter(["name"])
                        if p.info["name"] and filter.lower() in p.info["name"].lower()})
        return ", ".join(procs[:80]) or "None found."

    @tool("Close/kill every process whose name contains the given text.",
          name=("string", "Process name, e.g. chrome", True))
    def kill_process(self, name):
        targets = [p for p in psutil.process_iter(["name"]) if p.info["name"] and name.lower() in p.info["name"].lower()]
        if not targets:
            return "No matching process."
        if not self._ok(f"Confirm, close {len(targets)} process(es) named {name}? Yes or no."):
            return "Cancelled by user."
        for p in targets:
            try:
                p.terminate()
            except Exception:
                pass
        return f"Closed {len(targets)} process(es)."

    # ── apps & windows ────────────────────────────
    @tool("Open an application by name (e.g. chrome, spotify, notepad, excel, vscode).",
          name=("string", "Application name", True))
    def open_app(self, name):
        if IS_WIN:
            lnk = self._find_start_menu(name)
            if lnk:
                os.startfile(lnk)
                return f"Opened {lnk.stem}."
            subprocess.Popen(["cmd", "/c", "start", "", name], creationflags=NO_WINDOW)
        elif IS_MAC:
            subprocess.Popen(["open", "-a", name])
        else:
            subprocess.Popen([name.lower()], start_new_session=True)
        return f"Launching {name}."

    @staticmethod
    def _find_start_menu(name):
        dirs = [Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
                Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
                Path.home() / "Desktop"]
        n = name.lower().replace(" ", "")
        best = None
        for d in dirs:
            for lnk in d.rglob("*.lnk") if d.exists() else []:
                stem = lnk.stem.lower().replace(" ", "")
                if stem == n:
                    return lnk
                if n in stem and (best is None or len(lnk.stem) < len(best.stem)):
                    best = lnk
        return best

    @tool("Open a file, folder or URL with its default program.",
          target=("string", "Path or URL", True))
    def open_path(self, target):
        t = target if re.match(r"^[a-z]+://", target) else str(self._path(target))
        if IS_WIN:
            os.startfile(t)
        else:
            subprocess.Popen(["open" if IS_MAC else "xdg-open", t])
        return f"Opened {t}."

    @tool("Bring a window to the front by part of its title.",
          title=("string", "Part of the window title", True))
    def focus_window(self, title):
        if IS_WIN:
            import pygetwindow as gw
            wins = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
            if not wins:
                return "No window found."
            w = wins[0]
            if w.isMinimized:
                w.restore()
            w.activate()
            return f"Focused '{w.title}'."
        if IS_MAC:
            subprocess.run(["osascript", "-e", f'tell application "{title}" to activate'])
            return f"Activated {title}."
        return self.run_command(f"wmctrl -a '{title}'")

    # ── keyboard / mouse / media ──────────────────
    @tool("Type text into whatever window is focused (supports accents).",
          text=("string", "Text to type", True))
    def type_text(self, text):
        import pyautogui, pyperclip
        old = pyperclip.paste()
        pyperclip.copy(text)
        pyautogui.hotkey("command" if IS_MAC else "ctrl", "v")
        time.sleep(0.2)
        pyperclip.copy(old)
        return "Typed."

    @tool("Press a key or shortcut, e.g. 'enter', 'ctrl+s', 'alt+tab', 'win+d'.",
          keys=("string", "Keys joined with +", True))
    def press_keys(self, keys):
        import pyautogui
        pyautogui.hotkey(*[k.strip().lower() for k in keys.split("+")])
        return f"Pressed {keys}."

    @tool("Control media and volume.",
          action=("string", "play_pause | next | previous | volume_up | volume_down | mute", True),
          times=("integer", "Repeat count, e.g. 5 for volume steps", False))
    def media_control(self, action, times=1):
        import pyautogui
        key = {"play_pause": "playpause", "next": "nexttrack", "previous": "prevtrack",
               "volume_up": "volumeup", "volume_down": "volumedown", "mute": "volumemute"}.get(action)
        if not key:
            return "Unknown action."
        pyautogui.press(key, presses=max(1, int(times)), interval=0.05)
        return "Done."

    @tool("Take a screenshot and save it to the Pictures folder.")
    def screenshot(self):
        import pyautogui
        out = Path.home() / "Pictures" / f"jarvis_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        pyautogui.screenshot(str(out))
        return f"Saved {out}."

    @tool("Read the clipboard text.")
    def clipboard_read(self):
        import pyperclip
        return pyperclip.paste()[:4000] or "(clipboard empty)"

    @tool("Copy text to the clipboard.", text=("string", "Text", True))
    def clipboard_write(self, text):
        import pyperclip
        pyperclip.copy(text)
        return "Copied."

    # ── files ─────────────────────────────────────
    @tool("List a folder's contents.", path=("string", "Folder path, ~ = home. Default home.", False))
    def list_dir(self, path="~"):
        p = self._path(path)
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        return "\n".join(f"{'[DIR] ' if i.is_dir() else ''}{i.name}" for i in items[:150]) or "(empty)"

    @tool("Read a text file.", path=("string", "File path", True),
          max_chars=("integer", "Limit (default 6000)", False))
    def read_file(self, path, max_chars=6000):
        return self._path(path).read_text(encoding="utf-8", errors="replace")[: int(max_chars)]

    @tool("Create or overwrite a text file, or append to it.",
          path=("string", "File path", True), content=("string", "Text to write", True),
          append=("boolean", "Append instead of overwrite", False))
    def write_file(self, path, content, append=False):
        p = self._path(path)
        if not self._writable(p):
            return f"Blocked: {p} is outside allowed folders."
        if p.exists() and not append and not self._ok(f"Confirm, overwrite {p.name}? Yes or no."):
            return "Cancelled by user."
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a" if append else "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {p}."

    @tool("Find files by name pattern, e.g. '*.pdf' or '*factura*'.",
          pattern=("string", "Glob pattern", True), root=("string", "Where to search, default home", False))
    def search_files(self, pattern, root="~"):
        base, hits, t0 = self._path(root), [], time.time()
        for dirpath, dirnames, files in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "AppData", "Library")]
            for f in files:
                if fnmatch.fnmatch(f.lower(), pattern.lower()):
                    hits.append(os.path.join(dirpath, f))
            if len(hits) >= 40 or time.time() - t0 > 20:
                break
        return "\n".join(hits) or "Nothing found."

    @tool("Move a file or folder to the Recycle Bin / Trash.", path=("string", "Path", True))
    def delete_path(self, path):
        from send2trash import send2trash
        p = self._path(path)
        if not self._writable(p):
            return f"Blocked: {p} is outside allowed folders."
        if not self._ok(f"Confirm, send {p.name} to the trash? Yes or no."):
            return "Cancelled by user."
        send2trash(str(p))
        return f"Moved {p.name} to trash."

    @tool("Move or rename a file/folder.", source=("string", "From", True), destination=("string", "To", True))
    def move_path(self, source, destination):
        s, d = self._path(source), self._path(destination)
        if not (self._writable(s) and self._writable(d)):
            return "Blocked: outside allowed folders."
        shutil.move(str(s), str(d))
        return f"Moved to {d}."

    # ── seeing and clicking the screen ────────────
    def _ui(self):
        import uiautomation as auto
        auto.SetGlobalSearchTimeout(2)
        return auto

    @tool("Look at the window in front and list everything clickable on it - buttons, "
          "links, menu items, text boxes - with the exact name of each. ALWAYS call this "
          "before clicking, so you click a real thing instead of guessing.",
          limit=("integer", "How many to list, default 60", False))
    def see_screen(self, limit=60):
        try:
            auto = self._ui()
        except ImportError:
            return ("Screen control is not installed. Run: "
                    ".venv\\Scripts\\python -m pip install uiautomation")
        win = auto.GetForegroundControl().GetTopLevelControl()
        if not win:
            return "No window in front."
        out, seen = [f'Window: "{win.Name}"'], set()
        interesting = {"ButtonControl", "HyperlinkControl", "MenuItemControl", "TabItemControl",
                       "ListItemControl", "EditControl", "CheckBoxControl", "RadioButtonControl",
                       "ComboBoxControl", "TreeItemControl", "SplitButtonControl"}
        for ctrl, depth in auto.WalkControl(win, includeTop=False, maxDepth=14):
            try:
                name = (ctrl.Name or "").strip()
                kind = ctrl.ControlTypeName
                if not name or kind not in interesting:
                    continue
                r = ctrl.BoundingRectangle
                if r.width() <= 0 or r.height() <= 0:
                    continue
                key = (name, kind)
                if key in seen:
                    continue
                seen.add(key)
                label = kind.replace("Control", "")
                out.append(f'{label}: "{name[:70]}"  at ({r.xcenter()},{r.ycenter()})')
                if len(out) > int(limit):
                    break
            except Exception:
                continue
        return "\n".join(out) if len(out) > 1 else f'Window "{win.Name}" exposes nothing clickable.'

    @tool("Click something on screen by its name, exactly as see_screen listed it. This is "
          "how you press buttons, open links and pick menu items in any application.",
          name=("string", "The element's name, as see_screen showed it", True),
          double=("boolean", "Double-click instead of single", False))
    def click_element(self, name, double=False):
        try:
            auto = self._ui()
        except ImportError:
            return ("Screen control is not installed. Run: "
                    ".venv\\Scripts\\python -m pip install uiautomation")
        win = auto.GetForegroundControl().GetTopLevelControl()
        target, wanted = None, name.strip().lower()
        for ctrl, _ in auto.WalkControl(win, includeTop=False, maxDepth=14):
            try:
                n = (ctrl.Name or "").strip()
                if not n:
                    continue
                r = ctrl.BoundingRectangle
                if r.width() <= 0:
                    continue
                if n.lower() == wanted:          # exact wins
                    target = ctrl
                    break
                if target is None and wanted in n.lower():
                    target = ctrl
            except Exception:
                continue
        if target is None:
            return f'Nothing called "{name}" on screen. Call see_screen and use a name from it.'
        r = target.BoundingRectangle
        target.SetFocus()
        (target.DoubleClick if double else target.Click)(simulateMove=False)
        return f'Clicked "{target.Name[:60]}" at ({r.xcenter()},{r.ycenter()}).'

    @tool("Click at exact screen coordinates. Only use this when click_element cannot find "
          "the thing - prefer clicking things by name.",
          x=("integer", "X pixel", True), y=("integer", "Y pixel", True),
          double=("boolean", "Double-click", False), right=("boolean", "Right-click", False))
    def click_at(self, x, y, double=False, right=False):
        import pyautogui
        x, y = int(x), int(y)
        if right:
            pyautogui.rightClick(x, y)
        elif double:
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.click(x, y)
        return f"Clicked at ({x},{y})."

    @tool("Scroll the window in front.",
          direction=("string", "up or down", True),
          amount=("integer", "Notches, default 5", False))
    def scroll_screen(self, direction, amount=5):
        import pyautogui
        n = int(amount) * (1 if direction.lower() == "up" else -1)
        pyautogui.scroll(n * 120)
        return f"Scrolled {direction} {amount}."

    @tool("Type into the box that currently has focus, then optionally press Enter. "
          "Click the box first with click_element.",
          text=("string", "What to type", True),
          press_enter=("boolean", "Press Enter afterwards", False))
    def type_into(self, text, press_enter=False):
        import pyautogui, pyperclip, time as _t
        old = pyperclip.paste()
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        _t.sleep(0.15)
        pyperclip.copy(old)
        if press_enter:
            _t.sleep(0.1)
            pyautogui.press("enter")
        return f'Typed "{text[:50]}"' + (" and pressed Enter." if press_enter else ".")

    # ── research (needs the internet; everything else is offline) ──
    @tool("Search the web and get back the top results with titles, links and snippets. "
          "Needs an internet connection. Use it whenever the user asks about something "
          "you do not know, or anything current.",
          query=("string", "What to search for", True),
          count=("integer", "How many results, default 6", False))
    def web_search(self, query, count=6):
        import html as _html
        import urllib.parse
        import requests
        r = requests.post("https://html.duckduckgo.com/html/",
                          data={"q": query},
                          headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                          timeout=25)
        r.raise_for_status()
        out, seen = [], set()
        pattern = re.compile(
            r'result__a[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
            r'(?:.*?result__snippet[^>]*>(?P<snip>.*?)</a>)?', re.S)
        for m in pattern.finditer(r.text):
            url = _html.unescape(m.group("url"))
            if "duckduckgo.com/l/?uddg=" in url:            # unwrap the redirect
                q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                url = q.get("uddg", [url])[0]
            if url in seen:
                continue
            seen.add(url)
            strip = lambda s: _html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()
            out.append(f"{strip(m.group('title'))}\n  {url}\n  {strip(m.group('snip'))[:300]}")
            if len(out) >= int(count):
                break
        return "\n\n".join(out) or "No results. Check the internet connection."

    @tool("Read a web page and return its text, so you can actually use what a search found. "
          "Needs an internet connection.",
          url=("string", "Full URL", True),
          max_chars=("integer", "Limit, default 6000", False))
    def read_webpage(self, url, max_chars=6000):
        import html as _html
        import requests
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        r.raise_for_status()
        body = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", r.text)
        body = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", "\n", body)
        text = _html.unescape(re.sub(r"<[^>]+>", " ", body))
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
        return text[:int(max_chars)] or "That page had no readable text."

    # ── producing work ────────────────────────────
    @tool("Write a document and save it. Use this for anything long: a paper, a report, "
          "notes, a summary. Markdown headings in the text become real headings in Word. "
          "Say the whole document in the content argument, not a summary of it.",
          filename=("string", "File name, e.g. 'report.docx' or 'notes.md'", True),
          content=("string", "The full document text", True),
          folder=("string", "Where to save it, default the Documents folder", False))
    def write_document(self, filename, content, folder=""):
        base = self._path(folder) if folder else (Path.home() / "Documents")
        base.mkdir(parents=True, exist_ok=True)
        out = base / filename
        if not self._writable(out):
            return f"Blocked: {out} is outside allowed folders."
        if out.suffix.lower() == ".docx":
            try:
                from docx import Document
            except ImportError:
                return ("python-docx is not installed. Run: "
                        ".venv\\Scripts\\python -m pip install python-docx")
            doc = Document()
            for line in content.split("\n"):
                s = line.strip()
                if s.startswith("### "):
                    doc.add_heading(s[4:], level=3)
                elif s.startswith("## "):
                    doc.add_heading(s[3:], level=2)
                elif s.startswith("# "):
                    doc.add_heading(s[2:], level=1)
                elif s.startswith(("- ", "* ")):
                    doc.add_paragraph(s[2:], style="List Bullet")
                elif s:
                    doc.add_paragraph(s)
            doc.save(str(out))
        else:
            out.write_text(content, encoding="utf-8")
        return f"Saved {out} ({len(content.split())} words)."

    @tool("Run a snippet of Python and return whatever it prints. Use this for calculations, "
          "data work, bulk file operations, or anything fiddly. The standard library is "
          "available. Print what you want to know.",
          code=("string", "Python source. Use print() for output.", True),
          timeout=("integer", "Seconds, default 60", False))
    def run_python(self, code, timeout=60):
        import tempfile
        if not self._ok("I'm about to run a Python script. Is that alright?") and \
                re.search(r"\b(shutil\.rmtree|os\.remove|os\.unlink|subprocess|socket)\b", code):
            return "Cancelled by user."
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         encoding="utf-8") as f:
            f.write(code)
            path = f.name
        try:
            p = subprocess.run([sys.executable, path], capture_output=True, text=True,
                               timeout=int(timeout), cwd=str(Path.home()),
                               creationflags=NO_WINDOW)
            out = ((p.stdout or "") + (p.stderr or "")).strip()
            return out[-3500:] if out else "Ran with no output. Did you forget print()?"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    @tool("Schedule something to run automatically, every day or once at a given time, "
          "using Windows Task Scheduler.",
          name=("string", "A short name for the task", True),
          command=("string", "The command line to run", True),
          when=("string", "DAILY HH:MM, WEEKLY HH:MM, HOURLY, or ONCE HH:MM", True))
    def schedule_task(self, name, command, when):
        if not IS_WIN:
            return "Scheduling is only wired up for Windows."
        parts = when.strip().upper().split()
        kind = parts[0]
        at = parts[1] if len(parts) > 1 else "09:00"
        if kind not in ("DAILY", "WEEKLY", "HOURLY", "ONCE"):
            return "Use DAILY, WEEKLY, HOURLY or ONCE, with a time like 09:00."
        if not self._ok(f"I'm about to schedule '{name}' to run {when.lower()}. Go ahead?"):
            return "Cancelled by user."
        args = ["schtasks", "/Create", "/TN", name, "/TR", command, "/SC", kind, "/F"]
        if kind != "HOURLY":
            args += ["/ST", at]
        p = subprocess.run(args, capture_output=True, text=True, creationflags=NO_WINDOW)
        ok = p.returncode == 0
        return (f"Scheduled '{name}' to run {when.lower()}." if ok
                else f"Could not schedule it: {(p.stderr or p.stdout).strip()[:300]}")

    @tool("List or remove scheduled tasks you created.",
          action=("string", "list or delete", True),
          name=("string", "Task name, required for delete", False))
    def manage_scheduled_tasks(self, action, name=""):
        if not IS_WIN:
            return "Scheduling is only wired up for Windows."
        if action == "list":
            p = subprocess.run(["schtasks", "/Query", "/FO", "TABLE"], capture_output=True,
                               text=True, creationflags=NO_WINDOW)
            return (p.stdout or "")[-3000:]
        if action == "delete":
            if not name:
                return "Which task?"
            if not self._ok(f"Delete the scheduled task '{name}'?"):
                return "Cancelled by user."
            p = subprocess.run(["schtasks", "/Delete", "/TN", name, "/F"], capture_output=True,
                               text=True, creationflags=NO_WINDOW)
            return "Deleted." if p.returncode == 0 else (p.stderr or p.stdout).strip()[:300]
        return "Use list or delete."

    # ── changing itself ───────────────────────────
    @tool("Show every setting the user can change, with its current value.")
    def show_settings(self):
        import settings
        return settings.describe(self.cfg)

    @tool("Change one of your own settings. Use show_settings first if unsure of the name. "
          "Names: assistant_name, user_name, hotkey, language, follow_up_s, custom_instructions, "
          "llm.model, llm.temperature, stt.model_size, tts.rate, safety.confirm_dangerous.",
          name=("string", "Setting name exactly as listed", True),
          value=("string", "New value", True))
    def change_setting(self, name, value):
        import settings
        try:
            msg, _ = settings.set_value(self.cfg, name, value)
        except (KeyError, ValueError) as e:
            return f"Could not change it: {e}"
        if self.on_reload:
            self.on_reload()
        return msg

    @tool("Add a standing instruction about how you should behave from now on, such as "
          "'always answer in one sentence' or 'never ask before opening apps'. This is "
          "remembered permanently and shapes every future reply.",
          instruction=("string", "The instruction, in plain words", True))
    def add_instruction(self, instruction):
        import settings
        current = (self.cfg.get("custom_instructions") or "").strip()
        merged = f"{current}\n- {instruction.strip()}".strip() if current else f"- {instruction.strip()}"
        try:
            settings.set_value(self.cfg, "custom_instructions", merged)
        except ValueError as e:
            return f"Could not save it: {e}"
        if self.on_reload:
            self.on_reload()
        return "Noted, I'll do that from now on."

    @tool("Remove all the standing instructions the user has given about your behaviour.")
    def clear_instructions(self):
        import settings
        settings.set_value(self.cfg, "custom_instructions", "")
        if self.on_reload:
            self.on_reload()
        return "Cleared. Back to my normal behaviour."

    @tool("Add another spelling for your own name, for when speech recognition mishears it.",
          spelling=("string", "How it got transcribed, e.g. 'travis'", True))
    def add_wake_word(self, spelling):
        import settings
        words = list(self.cfg.get("wake_words") or [])
        s = spelling.strip().lower()
        if s in words:
            return f"'{s}' already wakes me."
        words.append(s)
        settings.set_value(self.cfg, "wake_words", words)
        if self.on_reload:
            self.on_reload()
        return f"I'll answer to '{s}' as well now."

    # ── memory ────────────────────────────────────
    @tool("Permanently remember a fact or preference about the user.", fact=("string", "The fact", True))
    def remember(self, fact):
        return self.memory.add(fact)

    @tool("Forget remembered facts containing some text.", text=("string", "Text to match", True))
    def forget(self, text):
        return self.memory.remove(text)

    # used in the system prompt
    @staticmethod
    def os_description():
        return f"{platform.system()} {platform.release()} ({platform.machine()}), user home {Path.home()}"
