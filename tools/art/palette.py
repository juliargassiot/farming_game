#!/usr/bin/env python3
"""Recolours art into one of the palettes in data/palette.json so every piece of a district shares its colours.
Each pixel takes the nearest palette colour by weighted RGB distance, so shading and detail survive and only the hues
change. `palette.py <name> <in.png> <out.png>` recolours one image; `palette.py <name>` writes previews/art/palette-<name>.png."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = np.array([0.6, 0.8, 0.5])


def load(name: str) -> dict:
    return json.loads((ROOT / "data" / "palette.json").read_text())[name]


def colours(palette: dict) -> np.ndarray:
    return np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for group in palette.values() for c in group], dtype=float)


def recolour(image: Image.Image, palette: dict) -> Image.Image:
    rgba = np.asarray(image.convert("RGBA")).astype(float)
    table = colours(palette)
    flat = rgba[..., :3].reshape(-1, 3)
    dist = ((flat[:, None, :] - table[None, :, :]) ** 2 * WEIGHTS).sum(axis=-1)
    out = rgba.copy()
    out[..., :3] = table[dist.argmin(axis=1)].reshape(rgba.shape[:2] + (3,))
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def swatch(name: str) -> Path:
    palette = load(name)
    cell, pad = 36, 8
    width = max(len(group) for group in palette.values()) * cell + 100
    sheet = Image.new("RGBA", (width, len(palette) * (cell + pad) + pad), (40, 40, 48, 255))
    draw = ImageDraw.Draw(sheet)
    for row, (group, entries) in enumerate(palette.items()):
        y = pad + row * (cell + pad)
        draw.text((pad, y + 12), group, fill=(230, 230, 230, 255))
        for col, c in enumerate(entries):
            x = 70 + col * cell
            draw.rectangle((x, y, x + cell - 2, y + cell - 2), fill=c)
    out = ROOT / "previews" / "art" / f"palette-{name}.png"
    sheet.save(out)
    return out


def main() -> None:
    name = sys.argv[1]
    if len(sys.argv) == 2:
        print("wrote", swatch(name).relative_to(ROOT))
        return
    recolour(Image.open(sys.argv[2]), load(name)).save(sys.argv[3])
    print("wrote", sys.argv[3])


if __name__ == "__main__":
    main()
