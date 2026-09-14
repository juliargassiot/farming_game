#!/usr/bin/env python3
"""A mountain district from data/mountain.json: a height field terraced into ledges, walls along every contour facing the
viewer, and a trail routed through waypoints. `layout` writes the district's cells into the map and `paint` draws the
same geometry into the painted ground, so what looks walkable is walkable. Run `mountain.py` to rewrite the map cells."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
TILE = 32
DATA = ROOT / "data" / "mountain.json"


def load() -> tuple[dict, tuple[int, int, int, int]]:
    data = json.loads(DATA.read_text())
    regions = json.loads((ROOT / "data" / "world.json").read_text())["regions"]
    x0, y0, x1, y1 = regions[data["region"]]["rect"]
    return data, (x0, y0, x1, y1)


def fbm(shape: tuple[int, int], cell: float, rng: np.random.Generator, octaves: int = 3) -> np.ndarray:
    total = np.zeros(shape)
    for i in range(octaves):
        c = cell / 2 ** i
        h, w = shape
        grid = rng.random((int(h / c) + 2, int(w / c) + 2))
        yy, xx = np.mgrid[0:h, 0:w] / c
        iy, ix = yy.astype(int), xx.astype(int)
        fy, fx = yy - iy, xx - ix
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        n = (grid[iy, ix] * (1 - fx) + grid[iy, ix + 1] * fx) * (1 - fy) + (grid[iy + 1, ix] * (1 - fx) + grid[iy + 1, ix + 1] * fx) * fy
        total += (n * 2 - 1) * 0.5 ** i
    return total / sum(0.5 ** i for i in range(octaves))


def terraces(data: dict, rect: tuple[int, int, int, int]) -> np.ndarray:
    """Terrace index per pixel of the district, 0 at the base: an elliptical rise to the peak, stepped, roughened by noise."""
    x0, y0, x1, y1 = rect
    h, w = (y1 - y0) * TILE, (x1 - x0) * TILE
    yy, xx = np.mgrid[0:h, 0:w] / TILE
    px, py = data["peak"][0] - x0, data["peak"][1] - y0
    dist = np.sqrt((xx - px) ** 2 + ((yy - py) / data["y_scale"]) ** 2)
    height = data["top"] - dist / data["step"] + data["noise"] * fbm((h, w), data["noise_size"] * TILE, np.random.default_rng(data["seed"]))
    for ax, ay in data["homes"]:
        cy, cx = ay - 0.5 - y0, ax + 4 - x0
        level = np.floor(height[int(cy * TILE), int(cx * TILE)])
        away = np.sqrt(np.maximum(np.abs(xx - cx) - 4.5, 0) ** 2 + np.maximum(np.abs(yy - cy) - 2.0, 0) ** 2)
        weight = np.clip(1 - away / 3.0, 0, 1) ** 2
        height = height * (1 - weight) + (level + 0.5) * weight
    return np.clip(np.floor(height), 0, 4).astype(np.int8)


def spline(points: list, samples: int = 12) -> list:
    """Catmull-Rom curve through the waypoints, in pixels."""
    pts = [np.array(p, dtype=float) * TILE for p in points]
    pts = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for t in np.linspace(0, 1, samples, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-2])
    return out


def trail_mask(data: dict, shape: tuple[int, int], rng: np.random.Generator) -> np.ndarray:
    """The trail as a soft-edged ribbon along its curve, in the world's pixel frame."""
    img = Image.new("L", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(img)
    for trail in data["trails"]:
        draw.line([(p[0], p[1]) for p in spline(trail)], fill=255, width=data["trail_width"], joint="curve")
    mask = np.asarray(img).astype(float) / 255
    kernel = np.ones(9) / 9
    for _ in range(2):
        mask = np.apply_along_axis(lambda m: np.convolve(m, kernel, "same"), 0, mask)
        mask = np.apply_along_axis(lambda m: np.convolve(m, kernel, "same"), 1, mask)
    return mask + fbm(shape, 16, rng, 2) * 0.18 > 0.5


def walls(terrace: np.ndarray, height: int) -> np.ndarray:
    """Depth into a wall per pixel (0 outside): a pixel is wall where higher ground lies within `height` pixels above it."""
    depth = np.zeros(terrace.shape, dtype=np.int16)
    for d in range(height, 0, -1):
        higher = np.zeros(terrace.shape, dtype=bool)
        higher[d:] = terrace[:-d] > terrace[d:]
        depth[higher] = d
    return depth


def geometry(data: dict, rect: tuple[int, int, int, int], world: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    terrace = terraces(data, rect)
    depth = walls(terrace, data["wall_height"])
    trail = trail_mask(data, world, np.random.default_rng(data["seed"] + 5))
    return terrace, depth, trail


def trail_cells(data: dict) -> list:
    """Cells the trail's centre line passes through, in order, with a bridge wherever it steps diagonally."""
    out = []
    for trail in data["trails"]:
        last = None
        for p in spline(trail, 32):
            cell = (int(p[0] // TILE), int(p[1] // TILE))
            if cell == last:
                continue
            if last and abs(cell[0] - last[0]) == 1 and abs(cell[1] - last[1]) == 1:
                out.append((cell[0], last[1]))
            out.append(cell)
            last = cell
    return out


def layout(rows: list, data: dict, rect: tuple[int, int, int, int]) -> list:
    """Rewrites the district's cells: walls and contour edges block, terraces are ledges, the base is grass, the trail
    cuts through everything, then homes and trees are stamped on."""
    x0, y0, x1, y1 = rect
    terrace, depth, trail = geometry(data, rect, (len(rows) * TILE, len(rows[0]) * TILE))
    rows = [list(r) for r in rows]
    for y in range(y0, y1):
        for x in range(x0, x1):
            t = terrace[(y - y0) * TILE:(y - y0 + 1) * TILE, (x - x0) * TILE:(x - x0 + 1) * TILE]
            d = depth[(y - y0) * TILE:(y - y0 + 1) * TILE, (x - x0) * TILE:(x - x0 + 1) * TILE]
            if (d > 0).mean() > 0.3 or t.max() != t.min():
                rows[y][x] = "^"
            else:
                rows[y][x] = "r" if t.max() > 0 else "."
    for x, y in trail_cells(data):
        rows[y][x] = "-"
    for ax, ay in data["homes"]:
        for y in range(ay - 2, ay + 1):
            for x in range(ax, ax + 8):
                rows[y][x] = "X"
        rows[ay][ax + 4] = "d"
    for key, symbol in (("trees", "T"), ("dead_trees", "t")):
        for x, y in data[key]:
            if rows[y][x] in ".r":
                rows[y][x] = symbol
    return ["".join(r) for r in rows]


def paint(img: np.ndarray, patch: np.ndarray, data: dict, rect: tuple[int, int, int, int], palette: dict, dials: dict, rng: np.random.Generator) -> np.ndarray:
    """Draws the district into the world image (and the trail wherever it runs) and returns a per-pixel surface code
    for the caller's sprig pass: 0 grass, 1 ledge, 2 wall, 4 trail. Walls get a lit lip, cracks, a dark foot, and a shadow on the ground below;
    contour edges without a wall get a dark rim."""
    x0, y0, x1, y1 = (v * TILE for v in rect)
    terrace, depth, trail = geometry(data, rect, img.shape[:2])
    view = img[y0:y1, x0:x1]
    local = patch[y0:y1, x0:x1]
    rock = np.array([_rgb(c) for c in palette["rock"]], dtype=int)
    cliff = {k: _rgb(v) for k, v in palette["cliff"].items()}
    grain = rng.integers(-7, 8, terrace.shape + (1,))
    ledge = terrace > 0
    view[ledge] = np.clip(rock[np.minimum(local, 1)] + grain, 0, 255)[ledge]
    district = np.where(ledge & (local < 2), 1, 0).astype(np.int8)
    wall = depth > 0
    frac = depth / data["wall_height"]
    shade = cliff["face"] * (0.92 - 0.4 * frac)[..., None] + grain * 2
    strata = ((depth + (fbm(terrace.shape, 40, rng, 1) * 4).astype(int)) % 9 == 0) & wall
    shade[strata] *= 0.8
    lip = wall & (depth <= 3)
    shade[lip] = cliff["lip"]
    shade[wall & (depth == 4)] = cliff["lip"] * 0.7 + cliff["face"] * 0.3
    foot = wall & (depth >= data["wall_height"] - 3) & ~np.roll(wall, -1, axis=0)
    cracks = (fbm(terrace.shape, 5, rng, 2) > 0.36) & wall & (depth > 4)
    shade[cracks] = cliff["crack"]
    view[wall] = np.clip(shade, 0, 255)[wall]
    view[foot] = cliff["foot"]
    edge = np.zeros_like(wall)
    edge[:, 1:] |= terrace[:, 1:] != terrace[:, :-1]
    edge[:, :-1] |= terrace[:, :-1] != terrace[:, 1:]
    edge[1:] |= terrace[1:] > terrace[:-1]
    edge[:-1] |= terrace[:-1] > terrace[1:]
    view[edge & ~wall] = cliff["foot"]
    district[wall | edge] = 2
    drop = np.zeros_like(wall)
    for d in range(1, 9):
        drop[d:] |= foot[:-d] & ~wall[d:]
    fall = np.zeros(terrace.shape)
    for d in range(1, 9):
        fall[d:] = np.where(foot[:-d] & ~wall[d:] & (fall[d:] == 0), 1 - d / 9, fall[d:])
    view[drop] = (view[drop] * (1 - 0.4 * fall[drop])[:, None]).astype(np.uint8)
    surface = np.zeros(img.shape[:2], dtype=np.int8)
    surface[y0:y1, x0:x1] = district
    dirt = np.array([_rgb(c) for c in palette["dirt"]], dtype=np.uint8)
    inner = trail.copy()
    inner[1:] &= trail[:-1]
    inner[:-1] &= trail[1:]
    inner[:, 1:] &= trail[:, :-1]
    inner[:, :-1] &= trail[:, 1:]
    img[trail] = dirt[1]
    img[trail & ~inner] = dirt[0]
    ys, xs = np.nonzero(inner)
    pick = rng.random(len(ys)) < dials["pebble_density"]
    for y, x in zip(ys[pick], xs[pick]):
        pw, ph = rng.integers(1, 4), rng.integers(1, 3)
        block = inner[y:y + ph, x:x + pw]
        img[y:y + ph, x:x + pw][block] = dirt[0] if rng.random() < 0.5 else dirt[2]
    slabs = rng.random(len(ys)) < dials["slab_density"]
    for y, x in zip(ys[slabs], xs[slabs]):
        pw, ph = rng.integers(5, 10), rng.integers(3, 6)
        block = inner[y:y + ph, x:x + pw]
        stone = np.zeros((ph, pw), dtype=bool)
        ry, rx = np.mgrid[0:ph, 0:pw]
        stone[((ry - ph / 2 + 0.5) / (ph / 2)) ** 2 + ((rx - pw / 2 + 0.5) / (pw / 2)) ** 2 <= 1] = True
        stone = stone[:block.shape[0], :block.shape[1]] & block
        img[y:y + ph, x:x + pw][stone] = rock[1 + rng.integers(0, 2)]
        img[y:y + ph, x:x + pw][stone & ~np.roll(stone, -1, axis=0)] = rock[0]
    steps = trail[y0:y1, x0:x1] & wall & (depth % 6 == 0)
    view[steps] = dirt[0]
    surface[trail] = 4
    return surface


def _rgb(text: str) -> np.ndarray:
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=int)


def main() -> None:
    data, rect = load()
    path = ROOT / "data" / "maps" / "world.txt"
    rows = path.read_text().strip().split("\n")
    rows = layout(rows, data, rect)
    if "--print" in sys.argv:
        x0, y0, x1, y1 = rect
        print("    " + "".join(str(x % 10) for x in range(x0, x1)))
        for y in range(y0, y1):
            print(f"{y:3d} " + rows[y][x0:x1])
        return
    path.write_text("\n".join(rows) + "\n")
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
