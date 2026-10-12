"""Settings window.

Two ways to change Jarvis, side by side:
  - the form, for the things with obvious values
  - the chat box, where you just say what you want changed and Jarvis does it
"""
import logging
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, scrolledtext

import settings as st

log = logging.getLogger("jarvis.settings_window")

BG = "#0e1014"
PANEL = "#161920"
EDGE = "#262b36"
TEXT = "#e7e9ef"
MUTED = "#7c8599"
BLUE = "#5b8cff"
GREEN = "#3ddc97"
RED = "#ff6b6b"

FORM = ["assistant_name", "user_name", "hotkey", "language", "llm.model",
        "stt.model_size", "follow_up_s", "tts.rate", "safety.confirm_dangerous"]


class SettingsWindow:
    def __init__(self, parent, cfg, engine, on_changed=None):
        self.cfg, self.engine, self.on_changed = cfg, engine, on_changed or (lambda: None)
        self.vars = {}

        self.win = tk.Toplevel(parent)
        self.win.title("Jarvis Settings")
        self.win.geometry("760x600")
        self.win.minsize(620, 500)
        self.win.configure(bg=BG)

        ui = tkfont.Font(family="Segoe UI", size=10)
        bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        title = tkfont.Font(family="Segoe UI Semibold", size=14)
        small = tkfont.Font(family="Segoe UI", size=8)

        tk.Label(self.win, text="SETTINGS", font=title, bg=BG, fg=TEXT).pack(
            anchor="w", padx=18, pady=(16, 2))
        tk.Label(self.win, text="Change anything below, or just tell Jarvis what you want at the bottom.",
                 font=ui, bg=BG, fg=MUTED).pack(anchor="w", padx=18, pady=(0, 10))

        # ── form ──────────────────────────────────────────────
        form = tk.Frame(self.win, bg=BG)
        form.pack(fill="x", padx=18)
        form.columnconfigure(1, weight=1)

        for row, name in enumerate(FORM):
            kind, help_text, restart = st.EDITABLE[name]
            tk.Label(form, text=name.split(".")[-1].replace("_", " ").title(),
                     font=bold, bg=BG, fg=TEXT).grid(row=row * 2, column=0, sticky="w", pady=(6, 0))

            cur = st._dig(cfg, name)
            if kind is bool:
                v = tk.BooleanVar(value=bool(cur))
                tk.Checkbutton(form, variable=v, bg=BG, fg=TEXT, selectcolor=PANEL,
                               activebackground=BG, bd=0, highlightthickness=0).grid(
                    row=row * 2, column=1, sticky="w", pady=(6, 0))
            elif name in st.CHOICES:
                v = tk.StringVar(value=str(cur))
                tk.OptionMenu(form, v, *st.CHOICES[name]).grid(row=row * 2, column=1,
                                                               sticky="w", pady=(6, 0))
            else:
                v = tk.StringVar(value="" if cur is None else str(cur))
                tk.Entry(form, textvariable=v, bg=PANEL, fg=TEXT, font=ui, bd=0,
                         insertbackground=TEXT, highlightthickness=1, highlightbackground=EDGE,
                         highlightcolor=BLUE).grid(row=row * 2, column=1, sticky="ew",
                                                   ipady=4, ipadx=6, pady=(6, 0))
            self.vars[name] = v
            tk.Label(form, text=help_text + ("   (restart to apply)" if restart else ""),
                     font=small, bg=BG, fg=MUTED).grid(row=row * 2 + 1, column=1,
                                                       sticky="w", pady=(1, 0))

        bar = tk.Frame(self.win, bg=BG)
        bar.pack(fill="x", padx=18, pady=(14, 6))
        tk.Button(bar, text="Save", command=self._save, font=bold, bg=BLUE, fg="#0b0d11",
                  bd=0, padx=20, pady=6, cursor="hand2").pack(side="left")
        tk.Button(bar, text="Reset everything", command=self._reset, font=ui, bg=PANEL,
                  fg=RED, bd=0, padx=14, pady=6, cursor="hand2").pack(side="left", padx=8)
        self.note = tk.Label(bar, text="", font=ui, bg=BG, fg=GREEN)
        self.note.pack(side="left", padx=10)

        # ── conversational ────────────────────────────────────
        tk.Frame(self.win, bg=EDGE, height=1).pack(fill="x", padx=18, pady=(8, 10))
        tk.Label(self.win, text="Or just tell Jarvis what to change",
                 font=bold, bg=BG, fg=TEXT).pack(anchor="w", padx=18)
        tk.Label(self.win, text='e.g. "keep your answers to one sentence", "stop asking before '
                                'you open apps", "you also answer to Travis", "speak slower"',
                 font=small, bg=BG, fg=MUTED).pack(anchor="w", padx=18, pady=(0, 6))

        self.chat = scrolledtext.ScrolledText(self.win, bg=PANEL, fg=TEXT,
                                              font=("Consolas", 9), bd=0, height=7,
                                              padx=12, pady=10, wrap="word", state="disabled")
        self.chat.pack(fill="both", expand=True, padx=18)
        self.chat.tag_config("you", foreground=BLUE)
        self.chat.tag_config("jarvis", foreground=GREEN)

        row = tk.Frame(self.win, bg=BG)
        row.pack(fill="x", padx=18, pady=12)
        self.entry = tk.Entry(row, bg=PANEL, fg=TEXT, font=ui, bd=0, insertbackground=TEXT,
                              highlightthickness=1, highlightbackground=EDGE, highlightcolor=BLUE)
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)
        self.entry.bind("<Return>", lambda e: self._ask())
        tk.Button(row, text="Send", command=self._ask, font=bold, bg=BLUE, fg="#0b0d11",
                  bd=0, padx=18, cursor="hand2").pack(side="left", padx=(8, 0), ipady=6)

        self._say("jarvis", "Tell me how you want me to behave and I'll change it myself.")

    # ── form actions ──────────────────────────────────────────
    def _save(self):
        changed, errors, restart = [], [], False
        for name, var in self.vars.items():
            try:
                new = st.coerce(name, var.get())
            except ValueError as e:
                errors.append(f"{name}: {e}")
                continue
            if new != st._dig(self.cfg, name):
                try:
                    _, needs = st.set_value(self.cfg, name, new)
                    changed.append(name)
                    restart = restart or needs
                except (KeyError, ValueError) as e:
                    errors.append(f"{name}: {e}")
        if errors:
            self.note.config(text="; ".join(errors)[:90], fg=RED)
            return
        self.on_changed()
        if not changed:
            self.note.config(text="Nothing changed.", fg=MUTED)
        else:
            self.note.config(
                text=f"Saved {len(changed)}." + (" Restart Jarvis to apply." if restart else ""),
                fg=GREEN)

    def _reset(self):
        if not messagebox.askyesno("Reset settings",
                                   "Undo every change and go back to the defaults?",
                                   parent=self.win):
            return
        fresh = st.reset()
        self.cfg.clear()
        self.cfg.update(fresh)
        for name, var in self.vars.items():
            var.set(st._dig(self.cfg, name))
        self.on_changed()
        self.note.config(text="Back to defaults. Restart Jarvis to apply all of it.", fg=GREEN)

    # ── conversational ────────────────────────────────────────
    def _say(self, who, text):
        self.chat.config(state="normal")
        self.chat.insert("end", f"{'You' if who == 'you' else 'Jarvis'}  ", who)
        self.chat.insert("end", f"{text}\n")
        self.chat.see("end")
        self.chat.config(state="disabled")

    def _ask(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._say("you", text)
        self._say("jarvis", "...")
        self.engine.send_text(
            "Change your own settings as follows, using your settings tools, then confirm "
            f"in one sentence what you changed: {text}")
        self.win.after(400, self._refresh_from_cfg)

    def _refresh_from_cfg(self, tries=30):
        """Pick up changes Jarvis made to itself while this window is open."""
        for name, var in self.vars.items():
            cur = st._dig(self.cfg, name)
            if cur is not None and str(var.get()) != str(cur):
                var.set(cur)
        if tries:
            self.win.after(700, lambda: self._refresh_from_cfg(tries - 1))

    def note_reply(self, text):
        """The console feeds Jarvis's spoken answers in here so the chat reads naturally."""
        try:
            self.chat.config(state="normal")
            last = self.chat.get("end-2l", "end-1c")
            if last.strip().endswith("..."):
                self.chat.delete("end-2l", "end-1c")
            self.chat.config(state="disabled")
        except Exception:
            pass
        self._say("jarvis", text)
