"""Jarvis control window and system-tray icon.

A small always-available app: shows what Jarvis is doing right now, logs
everything it hears and says, lets you type commands instead of speaking,
and hides to the system tray instead of quitting.
"""
import logging
import queue
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, scrolledtext

import assistant as eng

log = logging.getLogger("jarvis.gui")

# ── palette ───────────────────────────────────────────────────
BG = "#0e1014"
PANEL = "#161920"
EDGE = "#262b36"
TEXT = "#e7e9ef"
MUTED = "#7c8599"
BLUE = "#5b8cff"
GREEN = "#3ddc97"
AMBER = "#ffc857"
RED = "#ff6b6b"

STATUS_COLOR = {
    eng.LOADING: AMBER,
    eng.LISTENING: GREEN,
    eng.THINKING: BLUE,
    eng.SPEAKING: BLUE,
    eng.GOAHEAD: AMBER,
    eng.STANDBY_STATUS: MUTED,
    eng.MUTED: MUTED,
    eng.STOPPED: RED,
}

KIND_STYLE = {
    "you":    ("You",    BLUE),
    "jarvis": ("Jarvis", GREEN),
    "system": ("",       MUTED),
    "tool":   ("Action", AMBER),
    "error":  ("Error",  RED),
}


KEY_NAMES = {"cmd": "Win", "cmd_l": "Win", "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift",
             "space": "Space"}


def pretty_keys(combo: str) -> str:
    out = []
    for part in combo.split("+"):
        k = part.strip().strip("<>")
        out.append(KEY_NAMES.get(k, k.upper() if len(k) == 1 else k.title()))
    return " + ".join(out)


def tray_image(color=BLUE):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill="#0e1014", outline=color, width=5)
    d.ellipse((25, 25, 39, 39), fill=color)
    return img


class JarvisApp:
    def __init__(self, cfg):
        self.cfg = cfg
        self.name = cfg["assistant_name"]
        self.ui_q: "queue.Queue[tuple]" = queue.Queue()
        self.icon = None

        self.engine = eng.Assistant(
            cfg,
            on_event=lambda kind, text: self.ui_q.put(("event", kind, text)),
            on_status=lambda s: self.ui_q.put(("status", s, None)),
            on_confirm=self._confirm_dialog,
        )

        self.settings_win = None
        self._build_window()
        self.root.withdraw()                 # the panel is the everyday face, not this
        from panel import MicPanel
        self.panel = MicPanel(self.root, on_mic=self.talk_now, on_console=self.open_settings,
                              on_close=lambda: None, assistant_name=self.name)
        self.panel.show()
        self.engine.start()
        self._start_tray()
        self._start_hotkey()
        self.root.after(80, self._drain)

    # ── window ────────────────────────────────────────────────
    def _build_window(self):
        self.root = tk.Tk()
        self.root.title(f"{self.name} Control")
        self.root.geometry("760x560")
        self.root.minsize(560, 420)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        ui = tkfont.Font(family="Segoe UI", size=10)
        ui_bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        title_f = tkfont.Font(family="Segoe UI Semibold", size=15)
        mono = tkfont.Font(family="Consolas", size=10)

        # Header -------------------------------------------------
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(head, text=self.name.upper(), font=title_f, bg=BG, fg=TEXT).pack(side="left")

        self.status_dot = tk.Canvas(head, width=10, height=10, bg=BG, highlightthickness=0)
        self.status_dot.pack(side="right", padx=(8, 0))
        self._dot = self.status_dot.create_oval(1, 1, 9, 9, fill=AMBER, outline="")
        self.status_lbl = tk.Label(head, text=eng.LOADING, font=ui_bold, bg=BG, fg=AMBER)
        self.status_lbl.pack(side="right")

        tk.Frame(self.root, bg=EDGE, height=1).pack(fill="x", padx=18)

        # Transcript ---------------------------------------------
        self.logbox = scrolledtext.ScrolledText(
            self.root, bg=PANEL, fg=TEXT, font=mono, bd=0, relief="flat",
            insertbackground=TEXT, padx=14, pady=12, wrap="word", state="disabled")
        self.logbox.pack(fill="both", expand=True, padx=18, pady=12)
        for kind, (_, colour) in KIND_STYLE.items():
            self.logbox.tag_config(kind, foreground=colour)
            self.logbox.tag_config(kind + "_label", foreground=colour, font=ui_bold)

        # Input row ----------------------------------------------
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=18, pady=(0, 10))
        self.entry = tk.Entry(row, bg=PANEL, fg=TEXT, font=ui, bd=0, relief="flat",
                              insertbackground=TEXT, highlightthickness=1,
                              highlightbackground=EDGE, highlightcolor=BLUE)
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.insert(0, "")
        self._placeholder("Type a command instead of speaking...")

        tk.Button(row, text="Send", command=self._send, font=ui_bold, bg=BLUE, fg="#0b0d11",
                  bd=0, relief="flat", padx=18, activebackground="#7ba1ff",
                  cursor="hand2").pack(side="left", padx=(8, 0), ipady=6)

        # Buttons ------------------------------------------------
        btns = tk.Frame(self.root, bg=BG)
        btns.pack(fill="x", padx=18, pady=(0, 16))

        def mk(text, cmd, fg=TEXT):
            b = tk.Button(btns, text=text, command=cmd, font=ui, bg=PANEL, fg=fg, bd=0,
                          relief="flat", padx=14, pady=6, activebackground=EDGE,
                          activeforeground=TEXT, cursor="hand2")
            b.pack(side="left", padx=(0, 8))
            return b

        mk("Talk now", self.talk_now, AMBER)
        self.mic_btn = mk("Microphone: ON", self._toggle_mic, GREEN)
        mk("Settings", self.open_settings)
        mk("Clear", self._clear)
        mk("Hide", self.hide)
        self.hint = tk.Label(btns, text="", font=ui, bg=BG, fg=MUTED)
        self.hint.pack(side="right")

    def _placeholder(self, text):
        self._ph = text
        self.entry.insert(0, text)
        self.entry.config(fg=MUTED)

        def on_in(_):
            if self.entry.get() == self._ph:
                self.entry.delete(0, "end")
                self.entry.config(fg=TEXT)

        def on_out(_):
            if not self.entry.get().strip():
                self.entry.insert(0, self._ph)
                self.entry.config(fg=MUTED)

        self.entry.bind("<FocusIn>", on_in)
        self.entry.bind("<FocusOut>", on_out)

    # ── actions ───────────────────────────────────────────────
    def _send(self):
        text = self.entry.get().strip()
        if not text or text == self._ph:
            return
        self.entry.delete(0, "end")
        self.engine.send_text(text)

    def open_settings(self):
        if self.settings_win and tk.Toplevel.winfo_exists(self.settings_win.win):
            self.settings_win.win.deiconify(); self.settings_win.win.lift(); return
        from settings_window import SettingsWindow
        self.settings_win = SettingsWindow(self.root, self.cfg, self.engine,
                                           on_changed=self.engine.reload_config)

    def open_console(self):
        self.show()

    def talk_now(self):
        """Surface the mic panel and take the next thing said as a command."""
        try:
            self.panel.show()
        except Exception:
            self.show()
        self.engine.talk_now()

    def _start_hotkey(self):
        """Global shortcut, so Jarvis is reachable from anywhere without the wake word."""
        combos = self.cfg.get("hotkeys") or ([self.cfg["hotkey"]] if self.cfg.get("hotkey") else [])
        combos = [c.strip() for c in combos if c and c.strip()]
        if not combos:
            self.hint.config(text=f'model: {self.cfg["llm"]["model"]}')
            return
        pretty = pretty_keys(combos[0])
        try:
            from pynput import keyboard
            self._hk = keyboard.GlobalHotKeys(
                {c: (lambda: self.root.after(0, self.talk_now)) for c in combos})
            self._hk.daemon = True
            self._hk.start()
            self.hint.config(text=f"{pretty} to talk from anywhere")
            log.info("Global hotkeys registered: %s", combos)
        except Exception as e:
            log.warning("Could not register hotkeys %s: %s", combos, e)
            self.hint.config(text=f'model: {self.cfg["llm"]["model"]}')
            self.ui_q.put(("event", "system",
                           f"Could not register the {pretty} shortcut ({e}). "
                           f"The microphone button still works."))

    def _toggle_mic(self):
        on = not self.engine.mic_on
        self.engine.set_mic(on)
        self.mic_btn.config(text="Microphone: ON" if on else "Microphone: OFF",
                            fg=GREEN if on else MUTED)

    def _clear(self):
        self.logbox.config(state="normal")
        self.logbox.delete("1.0", "end")
        self.logbox.config(state="disabled")

    def _confirm_dialog(self, question):
        """Called from the engine thread; must bounce to the UI thread."""
        done, box = threading.Event(), {}

        def ask():
            self.show()
            box["v"] = messagebox.askyesno(f"{self.name} needs confirmation",
                                           question, parent=self.root)
            done.set()

        self.root.after(0, ask)
        done.wait(120)
        return box.get("v", False)

    # ── show / hide / quit ────────────────────────────────────
    def show(self):
        self.root.after(0, lambda: (self.root.deiconify(), self.root.lift(),
                                    self.root.focus_force()))

    def hide(self):
        self.root.withdraw()

    def quit(self):
        self.engine.stop()
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        self.root.after(0, self.root.destroy)

    # ── tray ──────────────────────────────────────────────────
    def _start_tray(self):
        """The tray icon is a nicety. If it cannot start, the window must still work."""
        try:
            import pystray
            menu = pystray.Menu(
                pystray.MenuItem("Talk now", lambda: self.root.after(0, self.talk_now),
                                 default=True),
                pystray.MenuItem("Show mic panel", lambda: self.root.after(0, self.panel.show)),
                pystray.MenuItem("Hide mic panel", lambda: self.root.after(0, self.panel.hide)),
                pystray.MenuItem("Console", lambda: self.root.after(0, self.show)),
                pystray.MenuItem("Settings", lambda: self.root.after(0, self.open_settings)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Microphone",
                                 lambda i, item: self.root.after(0, self._toggle_mic),
                                 checked=lambda item: self.engine.mic_on),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", lambda: self.quit()),
            )
            self.icon = pystray.Icon("jarvis", tray_image(), f"{self.name} assistant", menu)
            threading.Thread(target=self.icon.run, name="jarvis-tray", daemon=True).start()
        except Exception as e:
            self.icon = None
            log.warning("No tray icon (%s). The window still works.", e)
            self.ui_q.put(("event", "system",
                           "Tray icon unavailable; closing the window will quit Jarvis."))
            # Without a tray there is no way back, so the X button must quit, not hide
            self.root.protocol("WM_DELETE_WINDOW", self.quit)

    # ── pump engine events into the UI ────────────────────────
    def _drain(self):
        try:
            while True:
                what, a, b = self.ui_q.get_nowait()
                if what == "status":
                    self._set_status(a)
                else:
                    self._append(a, b)
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _set_status(self, status):
        colour = STATUS_COLOR.get(status, MUTED)
        self.status_lbl.config(text=status, fg=colour)
        self.status_dot.itemconfig(self._dot, fill=colour)
        try:
            self.panel.set_status(status, colour)
        except Exception:
            pass
        if self.icon:
            try:
                self.icon.icon = tray_image(colour)
            except Exception:
                pass

    def _append(self, kind, text):
        if kind in ("you", "jarvis", "error"):
            try:
                self.panel.set_line(text)
            except Exception:
                pass
        if kind in ("jarvis", "error") and self.settings_win:
            try:
                if tk.Toplevel.winfo_exists(self.settings_win.win):
                    self.settings_win.note_reply(text)
            except Exception:
                pass
        label, _ = KIND_STYLE.get(kind, ("", MUTED))
        self.logbox.config(state="normal")
        if label:
            self.logbox.insert("end", f"{label}  ", kind + "_label")
        self.logbox.insert("end", f"{text}\n", kind)
        self.logbox.see("end")
        self.logbox.config(state="disabled")

    def run(self):
        self.root.mainloop()
