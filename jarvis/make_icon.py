"""Generate jarvis.ico. Drawn at 8x and downscaled, so the small sizes stay crisp."""
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]
SS = 8
BG = (14, 16, 20, 255)
ACCENT = (91, 140, 255, 255)


def frame(px):
    """One icon at `px`, supersampled then resized with a good filter."""
    n = px * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = n / 64.0
    w = max(1, int(3.5 * u))

    d.ellipse([2 * u, 2 * u, 62 * u, 62 * u], fill=BG, outline=ACCENT, width=w)

    cx, cy = 32 * u, 29 * u
    cap_w, cap_h = 7.5 * u, 13 * u
    d.rounded_rectangle([cx - cap_w, cy - cap_h, cx + cap_w, cy + cap_h * 0.55],
                        radius=cap_w, fill=ACCENT)
    r = 13 * u
    d.arc([cx - r, cy - r * 0.45, cx + r, cy + r * 1.25], start=10, end=170,
          fill=ACCENT, width=w)
    d.line([cx, cy + r * 1.2, cx, cy + r * 1.75], fill=ACCENT, width=w)
    d.line([cx - 6.5 * u, cy + r * 1.75, cx + 6.5 * u, cy + r * 1.75], fill=ACCENT, width=w)

    return img.resize((px, px), Image.LANCZOS)


out = Path(__file__).resolve().parent / "jarvis.ico"
frames = [frame(s) for s in SIZES]
frames[-1].save(out, format="ICO", sizes=[(s, s) for s in SIZES],
                append_images=frames[:-1])
print(f"Wrote {out}")
