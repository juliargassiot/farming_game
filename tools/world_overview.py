#!/usr/bin/env python3
"""Renders data/maps/world.txt with region labels from data/world.json into previews/world-overview.png."""
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PX = 6
COLOURS = {
    ".": "#6abe30", "s": "#b08a58", "~": "#4fa3d8", "#": "#7a5020", "=": "#cdb07a", "B": "#d46a6a", "P": "#ffffff",
    ",": "#e6d6a2", "w": "#2f6fa8", "^": "#8c8c94", "M": "#4a3f55", "c": "#3b3340", "m": "#14101a", "%": "#4c6b58",
    ":": "#6b6448", "t": "#3d3128", "T": "#2c6a2a", '"': "#4f9a2a", "+": "#a8a29a", "H": "#6a3f2a", "D": "#a07848", "X": "#6a3f2a", "F": "#6a3f2a", "S": "#6a3f2a", "R": "#8a3f3a", "d": "#2a1a12", "b": "#d46a6a", "r": "#6b645d", "-": "#6a5138",
}


def main() -> None:
    rows = (ROOT / "data/maps/world.txt").read_text().strip().split("\n")
    world = json.loads((ROOT / "data/world.json").read_text())
    img = Image.new("RGB", (len(rows[0]) * PX, len(rows) * PX), "#000000")
    draw = ImageDraw.Draw(img)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            draw.rectangle((x * PX, y * PX, x * PX + PX - 1, y * PX + PX - 1), fill=COLOURS.get(ch, "#ff00ff"))
    for region in world["regions"].values():
        x0, y0, x1, y1 = [v * PX for v in region["rect"]]
        draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline="#ffffff")
        label = region["name"] + ((" (" + region["race"] + ")") if region["race"] else "")
        w = draw.textlength(label)
        cx, cy = (x0 + x1) / 2 - w / 2, (y0 + y1) / 2 - 6
        draw.rectangle((cx - 3, cy - 2, cx + w + 3, cy + 12), fill="#000000")
        draw.text((cx, cy), label, fill="#ffffff")
    out = ROOT / "previews/world-overview.png"
    img.save(out)
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
