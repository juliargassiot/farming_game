#!/usr/bin/env python3
"""Paints the ground as one continuous image per region and season: patches of three grass tones whose edges bleed into
each other through sprigs cut from the grass pack sheets, and flagstone paths where the map draws them, from data/grass.json.
Run `grass_paint.py` to write assets/grass/<region>_<season>.png."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TILE = 32
GRASSY = set(".PTt\"s=+")
TONES = ("dark", "mid", "light")
PATH = 3

PACK = ROOT / "tools" / "art" / "raw" / "grass_pack"


class Tuft:
    """One sprig cut from a pack sheet: which pixels are dark or light blades, which keep their own flower colour
    (a sprig that is mostly not green is a coloured grass, so all of it becomes blades), and the shadow it casts."""

    def __init__(self, rgba: np.ndarray, shadow: np.ndarray, origin: tuple[int, int], pack: dict) -> None:
        solid = rgba[..., 3] >= 128
        rgb = rgba[..., :3].astype(int)
        green = (rgb[..., 1] > rgb[..., 0] + 6) & (rgb[..., 1] > rgb[..., 2] + 6)
        luma = rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114
        split = np.median(luma[solid & green]) if (solid & green).any() else 0
        petals = solid & ~green
        if petals.sum() > pack["max_flower_share"] * solid.sum():
            green, petals = solid, np.zeros_like(solid)
            split = np.median(luma[solid])
        self.dark = solid & green & (luma <= split)
        self.light = solid & green & (luma > split)
        self.flower = petals
        self.rgb = rgba[..., :3]
        self.shadow = shadow.astype(float) / 255
        self.origin = origin
        self.shape = solid.shape


def _components(alpha: np.ndarray) -> list:
    """Bounding boxes of 8-connected opaque blobs."""
    h, w = alpha.shape
    seen = np.zeros_like(alpha)
    boxes = []
    for y, x in zip(*np.nonzero(alpha)):
        if seen[y, x]:
            continue
        stack, pts = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            pts.append((cy, cx))
            for ny in range(max(0, cy - 1), min(h, cy + 2)):
                for nx in range(max(0, cx - 1), min(w, cx + 2)):
                    if alpha[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        ys, xs = zip(*pts)
        boxes.append((min(ys), min(xs), max(ys) + 1, max(xs) + 1, len(pts)))
    return boxes


def load_tufts(sheet: str, pack: dict) -> list:
    """Every sprig on a pack sheet whose size fits the dials, with the shadow pixels that touch it."""
    rgba = np.asarray(Image.open(PACK / f"{sheet}.png").convert("RGBA"))
    shadow = np.asarray(Image.open(PACK / f"{sheet.replace('Grass', 'Grass Shadow')}.png").convert("RGBA"))[..., 3]
    reach = pack["shadow_reach"]
    out = []
    for y0, x0, y1, x1, count in _components(rgba[..., 3] >= 128):
        if count < pack["min_pixels"] or max(y1 - y0, x1 - x0) > pack["max_size"]:
            continue
        sy1, sx1 = min(rgba.shape[0], y1 + reach), min(rgba.shape[1], x1 + reach * 3)
        crop = rgba[y0:sy1, x0:sx1]
        cast = shadow[y0:sy1, x0:sx1] > 0
        keep = crop[..., 3] >= 128
        for _ in range(reach * 3):
            grown = np.zeros_like(keep)
            for dy, dx in ((0, 1), (1, 0), (1, 1), (0, -1), (-1, 0), (-1, 1), (1, -1), (-1, -1)):
                grown[max(0, dy):keep.shape[0] + min(0, dy), max(0, dx):keep.shape[1] + min(0, dx)] |= keep[max(0, -dy):keep.shape[0] + min(0, -dy), max(0, -dx):keep.shape[1] + min(0, -dx)]
            keep = keep | (grown & cast)
        out.append(Tuft(crop, np.where(keep & cast, shadow[y0:sy1, x0:sx1], 0), ((y1 - y0) // 2, (x1 - x0) // 2), pack))
    return out


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


def path_mask(rows: list[str], dials: dict, rng: np.random.Generator) -> np.ndarray:
    """Stone wherever the map draws a path or cobbled square, its corners rounded and its edge wobbled so it reads as laid by hand."""
    cells = np.array([[c in "=+" for c in row] for row in rows])
    mask = np.kron(cells, np.ones((TILE, TILE), dtype=bool)).astype(float)
    radius = dials["path_round"]
    kernel = np.ones(2 * radius + 1) / (2 * radius + 1)
    for _ in range(2):
        mask = np.apply_along_axis(lambda m: np.convolve(m, kernel, "same"), 0, mask)
        mask = np.apply_along_axis(lambda m: np.convolve(m, kernel, "same"), 1, mask)
    wobble = fbm(mask.shape, dials["wobble_size"], rng, 2) * dials["path_wobble"]
    return mask + wobble > 0.5


def flagstones(img: np.ndarray, mask: np.ndarray, stone: dict, dials: dict, rng: np.random.Generator) -> None:
    """Rows of rectangular stones in a running bond wherever the mask is set: each course offset by half a stone and
    every stone its own shade, a lit top edge, a shaded bottom edge, a grain of noise, and mortar in every gap and
    around the outer rim. The courses run on world coordinates, so regions cut from the same painting line up."""
    h, w = mask.shape
    mortar, shades = hex_rgb(stone["mortar"]), np.array([hex_rgb(c) for c in stone["shades"]], dtype=int)
    stone_w, stone_h = dials["stone_size"]
    course = np.arange(h) // stone_h
    offset = (course % 2) * (stone_w // 2)
    column = (np.arange(w)[None, :] + offset[:, None]) // stone_w
    pick = np.zeros((h // stone_h + 2, w // stone_w + 2), dtype=int)
    pick[...] = rng.integers(0, len(shades), pick.shape)
    fill = shades[pick[course[:, None], column]]
    fill = np.clip(fill + rng.integers(-dials["stone_grain"], dials["stone_grain"] + 1, (h, w, 1)), 0, 255)
    top = np.arange(h) % stone_h == 1
    bottom = np.arange(h) % stone_h == stone_h - 1
    left = (np.arange(w)[None, :] + offset[:, None]) % stone_w == 1
    right = (np.arange(w)[None, :] + offset[:, None]) % stone_w == stone_w - 1
    lit, shaded = dials["stone_light"], dials["stone_shade"]
    fill = np.where((top[:, None] | left)[..., None], np.clip(fill + lit, 0, 255), fill)
    fill = np.where((bottom[:, None] | right)[..., None], np.clip(fill - shaded, 0, 255), fill)
    gap = (np.arange(h) % stone_h == 0)[:, None] | ((np.arange(w)[None, :] + offset[:, None]) % stone_w == 0)
    fill[gap] = mortar
    inner = mask.copy()
    inner[1:] &= mask[:-1]
    inner[:-1] &= mask[1:]
    inner[:, 1:] &= mask[:, :-1]
    inner[:, :-1] &= mask[:, 1:]
    img[mask] = mortar
    img[inner] = fill[inner].astype(np.uint8)


def hex_rgb(text: str) -> np.ndarray:
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.uint8)


def _draw(img: np.ndarray, tuft: Tuft, cy: int, cx: int, colours: np.ndarray, shadow: float) -> None:
    """Stamps one sprig with its centre at (cy, cx): shadow darkens the ground, then blades take the palette's shades."""
    h, w = img.shape[:2]
    y0, x0 = cy - tuft.origin[0], cx - tuft.origin[1]
    y1, x1 = min(h, y0 + tuft.shape[0]), min(w, x0 + tuft.shape[1])
    ty, tx = max(0, -y0), max(0, -x0)
    y0, x0 = max(0, y0), max(0, x0)
    if y1 <= y0 or x1 <= x0:
        return
    region = img[y0:y1, x0:x1]
    sl = (slice(ty, ty + y1 - y0), slice(tx, tx + x1 - x0))
    region[...] = (region * (1 - shadow * tuft.shadow[sl][..., None])).astype(np.uint8)
    region[tuft.dark[sl]] = colours[0]
    region[tuft.light[sl]] = colours[2]
    region[tuft.flower[sl]] = tuft.rgb[sl][tuft.flower[sl]]


def paint(tone: np.ndarray, palette: dict, dials: dict, tufts: list, rng: np.random.Generator) -> np.ndarray:
    """Base fill per tone (paths get their flagstones), pack sprigs scattered in loose clumps inside each grass patch, and
    along every edge sprigs of the neighbouring grass reaching across, onto the next patch or the path, so they bleed."""
    h, w = tone.shape
    colours = np.array([[hex_rgb(c) for c in palette[name]] for name in TONES], dtype=np.uint8)
    img = colours[np.minimum(tone, PATH - 1), 1]
    flagstones(img, tone == PATH, palette["stone"], dials, rng)
    clump_noise = fbm(tone.shape, dials["clump_size"], rng, 2)
    step, reach = dials["stamp_step"], dials["bleed"]
    gy, gx = np.mgrid[-2:h + 2:step, -2:w + 2:step]
    gx = gx + (np.arange(gy.shape[0])[:, None] % 2) * (step // 2)
    cy, cx = (gy + rng.integers(-1, step + 1, gy.shape)).ravel(), (gx + rng.integers(0, step, gx.shape)).ravel()
    iy, ix = np.clip(cy, 0, h - 1), np.clip(cx, 0, w - 1)
    here = tone[iy, ix]
    near = here
    for _ in range(2):
        sample = tone[np.clip(cy + rng.integers(-reach, reach + 1, cy.shape), 0, h - 1), np.clip(cx + rng.integers(-reach, reach + 1, cx.shape), 0, w - 1)]
        near = np.where(near == here, sample, near)
    bleed = near != here
    clumped = clump_noise[iy, ix] > dials["clump_above"]
    chance = np.where(bleed, dials["edge_density"], np.where(clumped, dials["clump_density"], dials["stray_density"]))
    draw = rng.random(cy.shape) < chance
    picked = np.where(bleed, near, here)
    draw &= picked != PATH
    shapes = rng.integers(0, len(tufts), cy.shape)
    for i in np.nonzero(draw)[0]:
        _draw(img, tufts[shapes[i]], cy[i], cx[i], colours[picked[i]], dials["shadow"])
    return img


def paint_world(rows: list[str], data: dict, season: str) -> np.ndarray:
    dials = data["dials"]
    shape = (len(rows) * TILE, len(rows[0]) * TILE)
    rng = np.random.default_rng(dials["seed"])
    tone = tone_field(shape, dials, rng)
    tone[path_mask(rows, dials, rng)] = PATH
    tufts = [tuft for sheet in data["seasons"][season]["sheets"] for tuft in load_tufts(sheet, data["pack"])]
    img = paint(tone, data["seasons"][season], dials, tufts, np.random.default_rng(dials["seed"] + 1))
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
