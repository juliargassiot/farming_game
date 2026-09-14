#!/usr/bin/env python3
"""Paints the ground as one continuous image per region and season: patches of three grass tones whose leafy edges bleed
into each other, drawn from data/grass.json dials. Run `grass_paint.py` to write assets/grass/<region>_<season>.png."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TILE = 32
GRASSY = set(".PTt\"s")
TONES = ("dark", "mid", "light")

TUFTS = (
    (".111.", "11.11", "1...1"),
    ("..111..", ".11111.", "11...11", "1.....1"),
    ("...11", "..111", ".111.", "11..."),
    (".11.", "1111", ".11."),
    ("1...1", "11.11", ".111."),
    (".11.11.", "1111111", ".11111.", "..1.1.."),
    ("..1111..", ".111111.", "11....11"),
    ("...1.", "..111", ".111.", "111..", "1...."),
    ("1....", "11...", ".11..", "..111", "...11"),
    (".11.", "1..1"),
    ("..11..", ".1111.", "11..11", "1....1"),
    (".1.", "111", "1.1"),
)


def _stamps() -> list:
    """Every crescent and leaf lobe and its mirror image."""
    out = []
    for rows in TUFTS:
        stamp = np.array([[c == "1" for c in row] for row in rows], dtype=bool)
        out += [stamp, stamp[:, ::-1]]
    return out


STAMPS = _stamps()


def value_noise(shape: tuple[int, int], cell: float, rng: np.random.Generator) -> np.ndarray:
    """Smoothly interpolated random lattice in -1..1."""
    h, w = shape
    grid = rng.random((int(h / cell) + 2, int(w / cell) + 2))
    yy, xx = np.mgrid[0:h, 0:w] / cell
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = yy - y0, xx - x0
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    n = (grid[y0, x0] * (1 - fx) + grid[y0, x0 + 1] * fx) * (1 - fy) + (grid[y0 + 1, x0] * (1 - fx) + grid[y0 + 1, x0 + 1] * fx) * fy
    return n * 2 - 1


def fbm(shape: tuple[int, int], cell: float, rng: np.random.Generator, octaves: int = 3) -> np.ndarray:
    total = sum(value_noise(shape, cell / 2 ** i, rng) * 0.5 ** i for i in range(octaves))
    return total / sum(0.5 ** i for i in range(octaves))


def tone_field(shape: tuple[int, int], dials: dict, rng: np.random.Generator) -> np.ndarray:
    """0 dark, 1 mid, 2 light per pixel: large rounded patches with a gentle wobble along their edges."""
    t = fbm(shape, dials["patch_size"], rng, 2) + dials["edge_wobble"] * fbm(shape, dials["wobble_size"], rng, 2)
    tone = np.ones(shape, dtype=np.int8)
    tone[t > dials["light_above"]] = 2
    tone[t < dials["dark_below"]] = 0
    return tone


def hex_rgb(text: str) -> np.ndarray:
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.uint8)


def _stamp(img: np.ndarray, cx: np.ndarray, cy: np.ndarray, colour: np.ndarray, shapes: np.ndarray) -> None:
    """Draws one lobe per position, centred on that pixel."""
    h, w = img.shape[:2]
    for k, stamp in enumerate(STAMPS):
        sel = shapes == k
        if not sel.any():
            continue
        for dy, dx in zip(*np.nonzero(stamp)):
            py, px = cy[sel] + dy - stamp.shape[0] // 2, cx[sel] + dx - stamp.shape[1] // 2
            ok = (py >= 0) & (py < h) & (px >= 0) & (px < w)
            img[py[ok], px[ok]] = colour[sel][ok]


def paint(tone: np.ndarray, palette: dict, dials: dict, rng: np.random.Generator) -> np.ndarray:
    """Base fill per tone, leaf lobes scattered in loose clumps inside each patch (dark ones, lighter where a soft noise
    says so), and along every patch edge lobes of the neighbouring tone reaching across so the two bleed into each other."""
    h, w = tone.shape
    colours = np.array([[hex_rgb(c) for c in palette[name]] for name in TONES], dtype=np.uint8)
    img = colours[tone, 1]
    shade_noise = fbm(tone.shape, dials["shade_size"], rng, 2)
    clump_noise = fbm(tone.shape, dials["clump_size"], rng, 2)
    step, reach = dials["stamp_step"], dials["bleed"]
    xs = np.arange(-2, w + 2, step)
    for row, gy in enumerate(np.arange(-2, h + 2, step)):
        n = len(xs)
        cx, cy = xs + (row % 2) * (step // 2) + rng.integers(0, step, n), gy + rng.integers(-1, step + 1, n)
        ix, iy = np.clip(cx, 0, w - 1), np.clip(cy, 0, h - 1)
        here = tone[iy, ix]
        near = here
        for _ in range(2):
            sample = tone[np.clip(cy + rng.integers(-reach, reach + 1, n), 0, h - 1), np.clip(cx + rng.integers(-reach, reach + 1, n), 0, w - 1)]
            near = np.where(near == here, sample, near)
        noise = shade_noise[iy, ix]
        bleed = near != here
        clumped = clump_noise[iy, ix] > dials["clump_above"]
        draw = bleed | (rng.random(n) < np.where(clumped, dials["clump_density"], dials["stray_density"]))
        picked = np.where(bleed, near, here)[draw]
        shade = np.where(bleed, 1, np.where(noise > dials["light_wisps_above"], 2, 0))[draw]
        _stamp(img, cx[draw], cy[draw], colours[picked, shade], rng.integers(0, len(STAMPS), draw.sum()))
    return img


def sprinkle(img: np.ndarray, tone: np.ndarray, flowers: dict, rng: np.random.Generator) -> None:
    """Two-pixel flowers, mostly on the light patches, in the season's colours."""
    if not flowers.get("colours"):
        return
    h, w = tone.shape
    count = int(h * w * flowers["density"])
    ys, xs = rng.integers(0, h, count), rng.integers(0, w - 1, count)
    keep = (tone[ys, xs] == 2) | (rng.random(count) < flowers["off_patch"])
    for y, x in zip(ys[keep], xs[keep]):
        colour = hex_rgb(flowers["colours"][rng.integers(0, len(flowers["colours"]))])
        img[y, x] = colour
        img[y, x + 1] = (colour * 0.8).astype(np.uint8)


def paint_world(rows: list[str], data: dict, season: str) -> np.ndarray:
    dials = data["dials"]
    shape = (len(rows) * TILE, len(rows[0]) * TILE)
    rng = np.random.default_rng(dials["seed"])
    tone = tone_field(shape, dials, rng)
    img = paint(tone, data["seasons"][season], dials, np.random.default_rng(dials["seed"] + 1))
    sprinkle(img, tone, data["seasons"][season].get("flowers", {}), np.random.default_rng(dials["seed"] + 2))
    return img


def grassy_regions(rows: list[str], regions: dict) -> dict:
    out = {}
    for name, region in regions.items():
        x0, y0, x1, y1 = region["rect"]
        if any(rows[y][x] in GRASSY for y in range(y0, y1) for x in range(x0, x1)):
            out[name] = (x0, y0, x1, y1)
    return out


def main() -> None:
    data = json.loads((ROOT / "data" / "grass.json").read_text())
    rows = (ROOT / "data" / "maps" / "world.txt").read_text().strip().split("\n")
    regions = grassy_regions(rows, json.loads((ROOT / "data" / "world.json").read_text())["regions"])
    out_dir = ROOT / "assets" / "grass"
    out_dir.mkdir(parents=True, exist_ok=True)
    seasons = sys.argv[1:] or list(data["seasons"])
    for season in seasons:
        world = paint_world(rows, data, season)
        for name, (x0, y0, x1, y1) in regions.items():
            Image.fromarray(world[y0 * TILE:y1 * TILE, x0 * TILE:x1 * TILE], "RGB").save(out_dir / f"{name}_{season}.png", optimize=True)
        print(f"{season}: {', '.join(regions)}")


if __name__ == "__main__":
    main()
