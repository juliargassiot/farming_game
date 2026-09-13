#!/usr/bin/env python3
"""Draws the Steam library artwork for the Farm shortcuts into deck/art/ (pixel scene, scaled up)."""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "deck" / "art"
SKY, SUN, CLOUD = (79, 163, 216), (250, 220, 90), (240, 246, 250)
GRASS, DIRT, LEAF, FRUIT = (106, 190, 48), (154, 106, 58), (79, 154, 58), (224, 74, 58)
DARK, INK, WHITE = (55, 80, 55), (30, 45, 30), (245, 245, 235)
WALL, ROOF, DOOR = (232, 214, 170), (178, 62, 50), (110, 70, 40)
SCALE = 10
SIZES = {"p": (60, 90), "wide": (92, 43), "hero": (192, 62)}
GLYPHS = {
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "a": [".....", ".....", ".###.", "....#", ".####", "#...#", ".####"],
    "r": [".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."],
    "m": [".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
}


def scene(w: int, h: int, horizon: int) -> Image.Image:
    img = Image.new("RGB", (w, h), SKY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, horizon, w, h], fill=GRASS)
    sun_y = horizon // 2 - 4
    d.ellipse([w - 14, sun_y, w - 5, sun_y + 9], fill=SUN)
    for cx, cy in ((6, 6), (w // 2 - 4, 9)):
        d.rectangle([cx, cy + 1, cx + 9, cy + 3], fill=CLOUD)
        d.rectangle([cx + 2, cy, cx + 6, cy + 1], fill=CLOUD)
    house_x = 4
    d.rectangle([house_x, horizon - 8, house_x + 12, horizon + 1], fill=WALL)
    d.polygon([(house_x - 1, horizon - 8), (house_x + 6, horizon - 14), (house_x + 13, horizon - 8)], fill=ROOF)
    d.rectangle([house_x + 5, horizon - 4, house_x + 7, horizon + 1], fill=DOOR)
    top = horizon + 4
    d.rectangle([3, top, w - 4, h - 4], fill=DIRT)
    row = top + 3
    while row + 3 < h - 4:
        x = 6
        while x + 2 < w - 5:
            d.point((x + 1, row), fill=LEAF)
            d.rectangle([x, row + 1, x + 2, row + 1], fill=LEAF)
            d.point((x + 1, row + 2), fill=FRUIT if (x // 3 + row) % 3 == 0 else LEAF)
            x += 4
        row += 5
    return img


def wordmark(text: str, scale: int, fill=WHITE) -> Image.Image:
    small = Image.new("RGBA", (len(text) * 6 + 1, 9), (0, 0, 0, 0))
    px = small.load()
    for i, ch in enumerate(text):
        for y, row in enumerate(GLYPHS[ch]):
            for x, cell in enumerate(row):
                if cell == "#":
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            px[i * 6 + x + 1 + dx, y + 1 + dy] = INK + (255,)
    for i, ch in enumerate(text):
        for y, row in enumerate(GLYPHS[ch]):
            for x, cell in enumerate(row):
                if cell == "#":
                    px[i * 6 + x + 1, y + 1] = fill + (255,)
    return small.resize((small.width * scale, small.height * scale), Image.NEAREST)


def stamp(img: Image.Image, mark: Image.Image, cx: int, y: int) -> None:
    img.paste(mark, (cx - mark.width // 2, y), mark)


def ribbon(img: Image.Image, text: str) -> None:
    mark = wordmark(text, SCALE // 2, fill=WHITE)
    band_h = mark.height + SCALE
    y = img.height - band_h - SCALE * 2
    ImageDraw.Draw(img).rectangle([0, y, img.width, y + band_h], fill=DARK)
    stamp(img, mark, img.width // 2, y + SCALE // 2)


def build(name: str, tag: str) -> None:
    for kind, (w, h) in SIZES.items():
        horizon = h // 2
        img = scene(w, h, horizon).resize((w * SCALE, h * SCALE), Image.NEAREST)
        if kind != "hero":
            stamp(img, wordmark("Farm", SCALE * 2), img.width // 2, SCALE * 3 if kind == "p" else SCALE * 1)
        if tag:
            ribbon(img, tag)
        img.save(OUT / f"{name}_{kind}.png", optimize=True)
    logo = wordmark("Farm", SCALE * 2)
    if tag:
        sub = wordmark(tag, SCALE)
        canvas = Image.new("RGBA", (max(logo.width, sub.width), logo.height + sub.height), (0, 0, 0, 0))
        stamp(canvas, logo, canvas.width // 2, 0)
        stamp(canvas, sub, canvas.width // 2, logo.height)
        logo = canvas
    logo.save(OUT / f"{name}_logo.png", optimize=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    build("farm", "")
    build("farm_stable", "STABLE")
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
