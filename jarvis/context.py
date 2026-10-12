"""What the user is doing right now.

Jarvis reads this before every reply, so vague requests like "close this",
"what am I looking at" or "save it here" resolve to something real.
"""
import logging
import sys
from datetime import datetime

log = logging.getLogger("jarvis.context")
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

SKIP = {"", "Program Manager", "Windows Input Experience", "Microsoft Text Input Application",
        "Settings", "Jarvis Control"}


def active_window():
    """(window title, program name) of whatever is in front."""
    try:
        if IS_WIN:
            import ctypes
            import psutil
            u = ctypes.windll.user32
            h = u.GetForegroundWindow()
            length = u.GetWindowTextLengthW(h)
            buf = ctypes.create_unicode_buffer(length + 1)
            u.GetWindowTextW(h, buf, length + 1)
            pid = ctypes.c_ulong()
            u.GetWindowThreadProcessId(h, ctypes.byref(pid))
            try:
                proc = psutil.Process(pid.value).name()
            except Exception:
                proc = ""
            return buf.value, proc
        if IS_MAC:
            import subprocess
            name = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first application process whose frontmost is true'],
                capture_output=True, text=True, timeout=3).stdout.strip()
            return name, name
    except Exception as e:
        log.debug("active_window failed: %s", e)
    return "", ""


def open_windows(limit=12):
    """Titles of the other windows the user has open."""
    try:
        if IS_WIN:
            import pygetwindow as gw
            seen, out = set(), []
            for t in gw.getAllTitles():
                t = t.strip()
                if t and t not in SKIP and t not in seen:
                    seen.add(t)
                    out.append(t if len(t) <= 60 else t[:57] + "...")
                if len(out) >= limit:
                    break
            return out
    except Exception as e:
        log.debug("open_windows failed: %s", e)
    return []


def clipboard_preview(limit=160):
    try:
        import pyperclip
        t = (pyperclip.paste() or "").strip().replace("\n", " ")
        return t if len(t) <= limit else t[:limit] + "..."
    except Exception:
        return ""


def describe() -> str:
    """One compact block for the system prompt."""
    lines = [f"Time: {datetime.now():%A %d %B %Y, %H:%M}"]

    title, proc = active_window()
    if title or proc:
        lines.append(f"Active window: \"{title}\"" + (f" (in {proc})" if proc else ""))
        lines.append("When the user says \"this\", \"that\", \"here\" or \"what I'm looking at\", "
                     "they almost certainly mean the active window above.")

    others = [w for w in open_windows() if w != title]
    if others:
        lines.append("Other open windows: " + "; ".join(others))

    clip = clipboard_preview()
    if clip:
        lines.append(f"Clipboard: \"{clip}\"")

    return "\n".join(lines)
