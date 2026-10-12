"""The floating mic panel: a small always-on-top bar, like a voice-input overlay.

Everything except the text is drawn with Pillow at 4x and downscaled, because
tkinter's own canvas shapes have no antialiasing and look ragged. Text stays as
canvas text, which tkinter renders cleanly.
"""
import json
import logging
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

log = logging.getLogger("jarvis.panel")

W, H = 240, 116
SS = 4                      # supersampling factor
RADIUS = 20
CHROMA = "#ff00ff"          # punched out to fake rounded corners on Windows

BG = (32, 36, 44, 255)
EDGE = (56, 62, 74, 255)
GREY = (138, 147, 166, 255)
BRIGHT = (231, 233, 239, 255)
DARK = (22, 25, 31, 255)
IDLE = (101, 109, 126, 255)

# hit boxes: name -> (x1, y1, x2, y2)
HITS = {
    "close": (W - 32, 4, W - 6, 28),
    "handle": (0, 0, W - 34, 30),
    "gear": (16, 50, 56, 90),
    "mic": (W // 2 - 26, 44, W // 2 + 26, 96),
    "help": (W - 56, 50, W - 16, 90),
}

POS_FILE = Path("data/panel_pos.json")


def _hit(x, y):
    for name, (x1, y1, x2, y2) in HITS.items():
        if x1 <= x <= x2 and y1 <= y <= y2:
            return name
    return None


def _gear(d, cx, cy, r, colour, s):
    """A gear that reads as a gear at 24 pixels: ring plus eight teeth."""
    import math
    for i in range(8):
        a = math.radians(i * 45)
        tx, ty = cx + math.cos(a) * r, cy + math.sin(a) * r
        d.ellipse([tx - 2.6 * s, ty - 2.6 * s, tx + 2.6 * s, ty + 2.6 * s], fill=colour)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=int(3.2 * s))
    hole = r * 0.42
    d.ellipse([cx - hole, cy - hole, cx + hole, cy + hole], fill=BG)


def _mic_glyph(d, cx, cy, colour, s):
    """Capsule, cradle arc and stem - the standard microphone silhouette."""
    cap_w, cap_h = 7.0 * s, 17.0 * s
    d.rounded_rectangle([cx - cap_w, cy - cap_h * 0.72, cx + cap_w, cy + cap_h * 0.28],
                        radius=cap_w, fill=colour)
    r = 11.5 * s
    d.arc([cx - r, cy - r * 0.62, cx + r, cy + r * 1.05],
          start=12, end=168, fill=colour, width=int(2.8 * s))
    d.line([cx, cy + r * 1.0, cx, cy + r * 1.45], fill=colour, width=int(2.8 * s))
    d.line([cx - 5.5 * s, cy + r * 1.45, cx + 5.5 * s, cy + r * 1.45],
           fill=colour, width=int(2.8 * s))


def render(accent, hover=None, ring=False):
    """One crisp image of the whole panel in a given state."""
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = SS

    d.rounded_rectangle([1 * s, 1 * s, (W - 1) * s, (H - 1) * s], radius=RADIUS * s,
                        fill=BG, outline=EDGE, width=int(1.4 * s))

    # drag handle
    hc = BRIGHT if hover == "handle" else GREY
    d.rounded_rectangle([(W / 2 - 17) * s, 13 * s, (W / 2 + 17) * s, 16.5 * s],
                        radius=2 * s, fill=hc)

    # close
    cc = BRIGHT if hover == "close" else GREY
    cx, cy, a = (W - 19) * s, 15 * s, 5.0 * s
    d.line([cx - a, cy - a, cx + a, cy + a], fill=cc, width=int(1.8 * s))
    d.line([cx - a, cy + a, cx + a, cy - a], fill=cc, width=int(1.8 * s))

    # gear
    _gear(d, 36 * s, 70 * s, 11 * s, BRIGHT if hover == "gear" else GREY, s)

    # help
    hcol = BRIGHT if hover == "help" else GREY
    qx, qy, qr = (W - 36) * s, 70 * s, 11 * s
    d.ellipse([qx - qr, qy - qr, qx + qr, qy + qr], outline=hcol, width=int(2.2 * s))
    d.arc([qx - 4.6 * s, qy - 7.0 * s, qx + 4.6 * s, qy + 1.0 * s],
          start=170, end=20, fill=hcol, width=int(2.2 * s))
    d.line([qx + 0.2 * s, qy - 1.0 * s, qx + 0.2 * s, qy + 2.6 * s], fill=hcol, width=int(2.2 * s))
    d.ellipse([qx - 1.3 * s, qy + 5.0 * s, qx + 1.3 * s, qy + 7.6 * s], fill=hcol)

    # mic button
    mx, my, mr = (W / 2) * s, 70 * s, 23 * s
    if ring:
        d.ellipse([mx - mr - 6 * s, my - mr - 6 * s, mx + mr + 6 * s, my + mr + 6 * s],
                  outline=accent, width=int(2.4 * s))
    glow = tuple(list(accent[:3]) + [60])
    if hover == "mic":
        d.ellipse([mx - mr - 3 * s, my - mr - 3 * s, mx + mr + 3 * s, my + mr + 3 * s], fill=glow)
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=accent)
    _mic_glyph(d, mx, my, DARK, s)

    return img.resize((W, H), Image.LANCZOS)


class MicPanel:
    """Small floating control. Owns its own Toplevel."""

    def __init__(self, root, on_mic, on_console, on_close, assistant_name="Jarvis"):
        self.root = root
        self.on_mic, self.on_console, self.on_close = on_mic, on_console, on_close
        self.name = assistant_name
        self._visible = False
        self._accent = IDLE
        self._ring = False
        self._hover = None
        self._cache = {}

        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:                                   # Windows: real rounded corners
            self.win.config(bg=CHROMA)
            self.win.attributes("-transparentcolor", CHROMA)
            self._bg = CHROMA
        except tk.TclError:                    # elsewhere: square but working
            self._bg = "#20242c"
            self.win.config(bg=self._bg)

        self.c = tk.Canvas(self.win, width=W, height=H, bg=self._bg, highlightthickness=0)
        self.c.pack()
        self._img_id = self.c.create_image(0, 0, anchor="nw")
        self.label = self.c.create_text(W / 2, 103, text="Starting...", fill="#8a93a6",
                                        font=("Segoe UI", 8), width=W - 20)
        self._paint()

        self.c.bind("<Button-1>", self._click)
        self.c.bind("<B1-Motion>", self._drag)
        self.c.bind("<Motion>", self._motion)
        self.c.bind("<Leave>", lambda e: self._set_hover(None))
        self._place()

    # ── painting ──────────────────────────────────────────────
    def _paint(self):
        key = (self._accent, self._hover, self._ring)
        if key not in self._cache:
            flat = Image.new("RGB", (W, H), self._bg)
            flat.paste(render(*key), (0, 0), render(*key))
            self._cache[key] = ImageTk.PhotoImage(flat)
        self._photo = self._cache[key]          # keep a reference or Tk drops it
        self.c.itemconfig(self._img_id, image=self._photo)

    def _set_hover(self, name):
        if name != self._hover:
            self._hover = name
            self.c.config(cursor="hand2" if name in ("gear", "mic", "help", "close") else "")
            self._paint()

    # ── input ─────────────────────────────────────────────────
    def _motion(self, e):
        self._set_hover(_hit(e.x, e.y))

    def _click(self, e):
        what = _hit(e.x, e.y)
        if what == "mic":
            self.on_mic()
        elif what == "gear":
            self.on_console()
        elif what == "help":
            self._help()
        elif what == "close":
            self.hide()
            self.on_close()
        elif what == "handle":
            self._dx = e.x_root - self.win.winfo_x()
            self._dy = e.y_root - self.win.winfo_y()

    def _drag(self, e):
        if self._hover == "handle" or hasattr(self, "_dx"):
            if not hasattr(self, "_dx"):
                return
            self.win.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")
            self._save_pos()

    def _help(self):
        from tkinter import messagebox
        messagebox.showinfo(
            self.name,
            f"Click the microphone, or press the shortcut anywhere in Windows, then speak.\n"
            f"Click it again to cancel.\n\n"
            f'You can also just say "{self.name}" followed by what you want, at any time.\n\n'
            f"The gear opens Settings, where you can change how {self.name} behaves just by "
            f"telling it what you want.\n\n"
            f"Drag the bar at the top to move this panel. The X hides it - {self.name} keeps "
            f"listening, and the tray icon by the clock brings it back.",
            parent=self.win)

    # ── position ──────────────────────────────────────────────
    def _place(self):
        try:
            p = json.loads(POS_FILE.read_text())
            x, y = int(p["x"]), int(p["y"])
        except Exception:
            sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
            x, y = (sw - W) // 2, sh - H - 110
        self.win.geometry(f"{W}x{H}+{x}+{y}")

    def _save_pos(self):
        try:
            POS_FILE.parent.mkdir(parents=True, exist_ok=True)
            POS_FILE.write_text(json.dumps({"x": self.win.winfo_x(), "y": self.win.winfo_y()}))
        except Exception:
            pass

    # ── public ────────────────────────────────────────────────
    def show(self):
        self._visible = True
        self.win.deiconify()
        self.win.attributes("-topmost", True)
        self.win.lift()

    def hide(self):
        self._visible = False
        self.win.withdraw()

    @property
    def visible(self):
        return self._visible

    def set_status(self, status, colour_hex):
        rgb = tuple(int(colour_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
        self._accent = IDLE if status in ("Mic off", "Stopped") else rgb
        self._ring = status == "Go ahead"
        self.c.itemconfig(self.label, text={
            "Loading": "Starting up, about 30 seconds...",
            "Listening": f'Say "{self.name}", or click the mic',
            "Go ahead": "Listening - go ahead, click to cancel",
            "Thinking": "Thinking...",
            "Speaking": "Speaking...",
            "Mic off": "Microphone off",
            "Standing by": 'Standing by - say "wake up"',
            "Stopped": "Stopped",
        }.get(status, status))
        self._paint()

    def set_line(self, text):
        t = (text or "").replace("\n", " ")
        self.c.itemconfig(self.label, text=t if len(t) <= 58 else t[:55] + "...")
