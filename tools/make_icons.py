"""Draw the meal planner's home-screen icons into planner/icons/.

A white steaming bowl on the planner's green. Needs Pillow
(pip install pillow); only rerun it if the icon design changes.

Usage (from the repo root): python3 tools/make_icons.py
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "planner" / "icons"
GREEN = (44, 106, 77, 255)   # --accent in planner/template.html
WHITE = (255, 255, 255, 255)
S = 1024                     # draw large, then scale down


def motif(d):
    """Bowl and steam, kept inside the central 60% so maskable crops are safe."""
    # Bowl: lower half of an ellipse, with a rim and a foot
    d.chord((262, 400, 762, 780), 0, 180, fill=WHITE)
    d.rounded_rectangle((232, 568, 792, 610), radius=21, fill=WHITE)
    d.rounded_rectangle((432, 760, 592, 800), radius=20, fill=WHITE)
    # Steam: three wavy lines (one sine period each), stamped as overlapping
    # dots because Pillow's thick polylines leave gaps on curves
    w, amp, top, bot, n = 32, 26, 250, 480, 400
    for x in (402, 512, 622):
        for t in range(n + 1):
            px = x + amp * math.sin(2 * math.pi * t / n)
            py = top + (bot - top) * t / n
            d.ellipse((px - w / 2, py - w / 2, px + w / 2, py + w / 2), fill=WHITE)


def square(full_bleed):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if full_bleed:
        d.rectangle((0, 0, S, S), fill=GREEN)
    else:
        d.rounded_rectangle((0, 0, S - 1, S - 1), radius=S // 5, fill=GREEN)
    motif(d)
    return img


def main():
    OUT.mkdir(exist_ok=True)
    rounded, bleed = square(False), square(True)
    outputs = {
        "icon-192.png": (rounded, 192),
        "icon-512.png": (rounded, 512),
        "maskable-512.png": (bleed, 512),
        "apple-touch-icon.png": (bleed, 180),  # iOS rounds the corners itself
        "favicon-32.png": (rounded, 32),
    }
    for name, (img, size) in outputs.items():
        img.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)
        print(f"planner/icons/{name}")


if __name__ == "__main__":
    main()
