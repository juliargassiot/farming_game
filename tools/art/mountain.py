#!/usr/bin/env python3
"""The mountain map from data/mountain.json: a height field terraced into ledges, broken walls below every contour that
faces the viewer, a rocky apron of boulders at the foot, crags and snow at the peak, and worn trails through waypoints.
`main` writes data/maps/<map>.txt and the homes into its .json; `paint` draws the same geometry into the painted ground,
so what looks walkable is walkable."""
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
TILE = 32
DATA = ROOT / "data" / "mountain.json"
HOME_W, HOME_H = 8, 3


def load() -> dict:
    return json.loads(DATA.read_text())


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


class Geometry:
    """Everything derived from the data at pixel resolution: height, terrace, wall depth, rubble, boulders, trail."""

    def __init__(self, data: dict) -> None:
        self.data = data
        w, h = data["size"]
        self.shape = (h * TILE, w * TILE)
        rng = np.random.default_rng(data["seed"])
        yy, xx = np.mgrid[0:self.shape[0], 0:self.shape[1]] / TILE
        px, py = data["peak"]
        dist = np.sqrt((xx - px) ** 2 + ((yy - py) / data["y_scale"]) ** 2)
        height = data["top"] - dist / data["step"] + data["noise"] * fbm(self.shape, data["noise_size"] * TILE, rng)
        for home in data["homes"]:
            ax, ay = home["at"]
            cy, cx = ay - 0.5, ax + HOME_W / 2
            level = np.floor(height[int(cy * TILE), int(cx * TILE)])
            away = np.sqrt(np.maximum(np.abs(xx - cx) - 4.5, 0) ** 2 + np.maximum(np.abs(yy - cy) - 2.0, 0) ** 2)
            weight = np.clip(1 - away / 3.0, 0, 1) ** 2
            height = height * (1 - weight) + (level + 0.5) * weight
        self.height = height
        self.terrace = np.clip(np.floor(height), 0, 4).astype(np.int8)
        self.rockiness = np.clip((height - (1 - data["apron"] / data["step"])) / (data["apron"] / data["step"]), 0, 1) * (self.terrace == 0)
        tall = data["wall_height"] * (1 + data["wall_vary"] * fbm(self.shape, 5 * TILE, rng, 2))
        crumble = fbm(self.shape, 5 * TILE, rng, 2) > data["crumble"]
        self.depth, self.rubble = self._walls(tall, crumble)
        self.trail = self._trail(np.random.default_rng(data["seed"] + 5))
        self.boulders = self._boulders(np.random.default_rng(data["seed"] + 9))

    def _walls(self, tall: np.ndarray, crumble: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Wall depth per pixel where higher ground lies within the local wall height above it; crumbled stretches
        become rubble instead of a face."""
        depth = np.zeros(self.shape, dtype=np.int16)
        rubble = np.zeros(self.shape, dtype=bool)
        limit = int(self.data["wall_height"] * (1 + self.data["wall_vary"])) + 1
        for d in range(limit, 0, -1):
            higher = np.zeros(self.shape, dtype=bool)
            higher[d:] = (self.terrace[:-d] > self.terrace[d:]) & (d <= tall[:-d])
            depth[higher & ~crumble] = d
            rubble |= higher & crumble
        return depth, rubble

    def _trail(self, rng: np.random.Generator) -> np.ndarray:
        """Trail strength per pixel: the first trail wears in from nothing over `trail_fade` tiles, the rest are full."""
        img = Image.new("L", (self.shape[1], self.shape[0]), 0)
        draw = ImageDraw.Draw(img)
        width = self.data["trail_width"]
        for i, trail in enumerate(self.data["trails"]):
            pts = spline(trail)
            fade = self.data["trail_fade"] * TILE if i == 0 else 0
            run = 0.0
            for a, b in zip(pts, pts[1:]):
                run += float(np.hypot(*(b - a)))
                s = min(1.0, 0.15 + 0.85 * run / fade) if fade else 1.0
                draw.line([tuple(a), tuple(b)], fill=int(255 * s), width=max(6, int(width * (0.4 + 0.6 * s))))
        mask = np.asarray(img).astype(float) / 255
        kernel = np.ones(9) / 9
        for _ in range(2):
            mask = np.apply_along_axis(lambda m: np.convolve(m, kernel, "same"), 0, mask)
            mask = np.apply_along_axis(lambda m: np.convolve(m, kernel, "same"), 1, mask)
        return np.clip(mask + fbm(self.shape, 16, rng, 2) * 0.18 * (mask > 0.05), 0, 1)

    def _boulders(self, rng: np.random.Generator) -> list:
        """Boulders as (cx, cy, rx, ry, crag): dense in rubble, thickening across the apron toward the first wall, a
        few on every ledge, and a ring of crags around the peak; never on a trail, a home, or the start."""
        rates = self.data["boulders"]
        h, w = self.shape
        near_peak = np.zeros(self.shape, dtype=bool)
        peak = self.terrace == 4
        for d in range(1, 36):
            near_peak[d:] |= peak[:-d] & ~peak[d:]
            near_peak[:-d] |= peak[d:] & ~peak[:-d]
            near_peak[:, d:] |= peak[:, :-d] & ~peak[:, d:]
            near_peak[:, :-d] |= peak[:, d:] & ~peak[:, :-d]
        chance = np.where(self.rubble, rates["rubble"], 0.0)
        chance += rates["apron"] * self.rockiness ** 1.2
        chance += np.where((self.terrace > 0) & (self.depth == 0), rates["ledge"] * (0.6 + 0.2 * self.terrace), 0.0)
        chance += np.where(near_peak, rates["crag"], 0.0)
        chance /= TILE * TILE
        keep_out = self.trail > 0.08
        sx, sy = self.data["start"]
        keep_out[(sy - 2) * TILE:(sy + 3) * TILE, (sx - 2) * TILE:(sx + 3) * TILE] = True
        for home in self.data["homes"]:
            ax, ay = home["at"]
            keep_out[max(0, ay - HOME_H - 4) * TILE:(ay + 2) * TILE, max(0, ax - 1) * TILE:(ax + HOME_W + 1) * TILE] = True
        out = []
        for y, x in zip(*np.nonzero(rng.random(self.shape) < chance)):
            crag, loose = near_peak[y, x], self.rubble[y, x]
            big = rng.random() < (0.05 if loose else 0.12 + 0.25 * self.rockiness[y, x])
            rx = rng.integers(8, 14) if crag else rng.integers(22, 40) if big else rng.integers(5, 12) if loose else rng.integers(9, 20)
            ry = int(rx * rng.uniform(1.8, 2.6)) if crag else int(rx * rng.uniform(0.6, 0.9))
            y0, y1, x0, x1 = max(0, y - ry - 6), min(h, y + ry + 12), max(0, x - rx - 8), min(w, x + rx + 8)
            gap = 0.4 if crag else 0.55 if loose else 1.0
            if keep_out[y0:y1, x0:x1].any() or any(abs(x - bx) < (rx + brx) * gap and abs(y - by) < (ry + bry) * gap for bx, by, brx, bry, _ in out):
                continue
            out.append((int(x), int(y), int(rx), int(ry), bool(crag)))
        return out


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


def trail_cells(data: dict) -> list:
    """Cells every trail's centre line passes through, with a bridge wherever it steps diagonally."""
    w, h = data["size"]
    out = []
    for trail in data["trails"]:
        last = None
        for p in spline(trail, 32):
            cell = (int(p[0] // TILE), int(p[1] // TILE))
            if cell == last or not (0 <= cell[0] < w and 0 <= cell[1] < h):
                continue
            if last and abs(cell[0] - last[0]) == 1 and abs(cell[1] - last[1]) == 1:
                out.append((cell[0], last[1]))
            out.append(cell)
            last = cell
    return out


def layout(geo: Geometry) -> list:
    """The map's cells: walls, rubble, boulders and contour edges block; terraces are ledges; the foot is grass; trails
    cut through everything; then homes, trees and the start are stamped on."""
    data = geo.data
    w, h = data["size"]
    solid = (geo.depth > 0) | geo.rubble
    for x, y, rx, ry, _ in geo.boulders:
        yy, xx = np.mgrid[max(0, y - ry):min(geo.shape[0], y + ry + 1), max(0, x - rx):min(geo.shape[1], x + rx + 1)]
        solid[yy.min():yy.max() + 1, xx.min():xx.max() + 1] |= ((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2 <= 1
    rows = [["." for _ in range(w)] for _ in range(h)]
    for y in range(h):
        for x in range(w):
            sl = (slice(y * TILE, (y + 1) * TILE), slice(x * TILE, (x + 1) * TILE))
            t = geo.terrace[sl]
            if solid[sl].mean() > 0.3 or solid[y * TILE + TILE // 2, x * TILE + TILE // 2] or t.max() != t.min():
                rows[y][x] = "^"
            elif t.max() > 0:
                rows[y][x] = "r"
    for x, y in trail_cells(data):
        rows[y][x] = "-"
    for y in range(h):
        for x in range(w):
            if rows[y][x] != "^" and geo.trail[y * TILE + TILE // 2, x * TILE + TILE // 2] > 0.5:
                rows[y][x] = "-"
    for home in data["homes"]:
        ax, ay = home["at"]
        for y in range(ay - HOME_H + 1, ay + 1):
            for x in range(ax, ax + HOME_W):
                rows[y][x] = "X"
        rows[ay][ax + HOME_W // 2] = "d"
    for key, symbol in (("trees", "T"), ("dead_trees", "t")):
        for x, y in data[key]:
            if rows[y][x] in ".r":
                rows[y][x] = symbol
    sx, sy = data["start"]
    rows[sy][sx] = "P"
    return ["".join(r) for r in rows]


def paint(img: np.ndarray, patch: np.ndarray, data: dict, palette: dict, dials: dict, rng: np.random.Generator) -> np.ndarray:
    """Draws the mountain into the map's painted ground and returns per-pixel surface codes for the sprig pass:
    0 grass, 1 rock ground, 2 wall or stone, 4 trail."""
    geo = Geometry(data)
    grass = img.astype(float)
    rock = np.array([_rgb(c) for c in palette["rock"]], dtype=float)
    cliff = {k: _rgb(v).astype(float) for k, v in palette["cliff"].items()}
    dirt = np.array([_rgb(c) for c in palette["dirt"]], dtype=float)
    snow = _rgb(palette["snow"]).astype(float)
    grain = rng.integers(-7, 8, geo.shape + (1,)).astype(float)
    ledge = geo.terrace > 0
    ground = np.where(ledge[..., None], rock[np.minimum(patch, 1)] + grain, grass)
    blend = (0.85 * geo.rockiness ** 0.8)[..., None]
    ground = np.where(ledge[..., None], ground, grass * (1 - blend) + (rock[1] + grain) * blend)
    view = ground
    stones = rng.random(geo.shape) < 0.08 * geo.rockiness
    for y, x in zip(*np.nonzero(stones)):
        view[y:y + rng.integers(1, 3), x:x + rng.integers(1, 4)] = rock[0] if rng.random() < 0.6 else rock[2]
    surface = np.where(ledge & (patch < 2), 1, 0).astype(np.int8)
    surface[(geo.rockiness > 0.35) & (patch < 2)] = 1
    wall = geo.depth > 0
    frac = geo.depth / (data["wall_height"] * (1 + data["wall_vary"]))
    shade = cliff["face"] * (0.92 - 0.45 * frac)[..., None] + grain * 2
    strata = ((geo.depth + (fbm(geo.shape, 40, rng, 1) * 4).astype(int)) % 9 == 0) & wall
    shade[strata] *= 0.8
    lip = wall & (geo.depth <= 3)
    shade[lip] = cliff["lip"]
    shade[wall & (geo.depth == 4)] = cliff["lip"] * 0.7 + cliff["face"] * 0.3
    cracks = (fbm(geo.shape, 5, rng, 2) > 0.36) & wall & (geo.depth > 4)
    shade[cracks] = cliff["crack"]
    view[wall] = shade[wall]
    foot = wall & ~np.roll(wall, -1, axis=0)
    view[foot] = cliff["foot"]
    edge = np.zeros_like(wall)
    edge[:, 1:] |= geo.terrace[:, 1:] != geo.terrace[:, :-1]
    edge[:, :-1] |= geo.terrace[:, :-1] != geo.terrace[:, 1:]
    edge[1:] |= geo.terrace[1:] > geo.terrace[:-1]
    edge[:-1] |= geo.terrace[:-1] > geo.terrace[1:]
    view[edge & ~wall] = cliff["foot"]
    surface[wall | edge | geo.rubble] = 2
    fall = np.zeros(geo.shape)
    for d in range(1, 9):
        fall[d:] = np.where(foot[:-d] & ~wall[d:] & (fall[d:] == 0), 1 - d / 9, fall[d:])
    view *= (1 - 0.4 * fall)[..., None]
    _boulders(view, geo, rock, cliff, rng)
    surface[_boulder_mask(geo)] = 2
    trail = geo.trail
    dirt_fill = np.where((geo.trail > 0.5)[..., None], dirt[1], dirt[1] * 0.9 + dirt[0] * 0.1)
    rim = trail - np.minimum.reduce([np.roll(trail, s, a) for s in (-2, 2) for a in (0, 1)])
    dirt_fill[rim > 0.12] = dirt[0]
    alpha = np.clip(trail * 1.6 - 0.2, 0, 1)[..., None]
    view[...] = view * (1 - alpha) + dirt_fill * alpha
    inner = trail > 0.55
    _pebbles(view, inner, dirt, rock, dials, rng)
    steps = inner & wall & (geo.depth % 6 == 0)
    view[steps] = dirt[0]
    _paws(view, data, geo, dirt[0], rng)
    surface[trail > 0.4] = 4
    reach = np.clip((geo.height - data["snow_from"]) / 0.3, 0, 1)
    dust = np.where(fbm(geo.shape, 22, rng, 2) > 0.3 - 0.55 * reach, 0.8, 0.0) * (reach > 0) * ~(wall & (geo.depth > 4)) * ~_boulder_mask(geo)
    for x, y, rx, ry, crag in geo.boulders:
        if crag and reach[y, x] > 0:
            y0, y1, x0, x1 = max(0, y - ry), y - ry // 4, max(0, x - rx), min(geo.shape[1], x + rx + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            dust[y0:y1, x0:x1] = np.where(_shape(xx, yy, x, y, rx, ry, True, 1.2), 0.95, dust[y0:y1, x0:x1])
    dust = dust[..., None]
    view[...] = view * (1 - dust) + snow * dust
    img[...] = np.clip(view, 0, 255).astype(np.uint8)
    return surface


def _shape(xx: np.ndarray, yy: np.ndarray, x: int, y: int, rx: int, ry: int, crag: bool, shrink: float = 0) -> np.ndarray:
    """A boulder is an ellipse; a crag narrows toward its top into a point."""
    width = rx * (0.3 + 0.7 * np.clip((yy - y + ry) / (2 * ry), 0, 1)) if crag else rx
    return ((xx - x) / np.maximum(width - shrink, 1)) ** 2 + ((yy - y) / max(ry - shrink, 1)) ** 2 <= 1


def _boulder_mask(geo: Geometry) -> np.ndarray:
    mask = np.zeros(geo.shape, dtype=bool)
    for x, y, rx, ry, crag in geo.boulders:
        y0, y1, x0, x1 = max(0, y - ry), min(geo.shape[0], y + ry + 1), max(0, x - rx), min(geo.shape[1], x + rx + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        mask[y0:y1, x0:x1] |= _shape(xx, yy, x, y, rx, ry, crag)
    return mask


def _boulders(view: np.ndarray, geo: Geometry, rock: np.ndarray, cliff: dict, rng: np.random.Generator) -> None:
    """Each boulder: a cast shadow on the ground, a dark outline, a body lit from the top left, a crack or two;
    crags are the same shape stretched tall, darker, with a snow cap where the peak's dusting reaches."""
    h, w = geo.shape
    for x, y, rx, ry, crag in geo.boulders:
        y0, y1, x0, x1 = max(0, y - ry - 2), min(h, y + ry + 8), max(0, x - rx - 2), min(w, x + rx + 6)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        body = _shape(xx, yy, x, y, rx, ry, crag)
        cast = _shape(xx, yy, x + 3, y + 5, rx + 1, ry + 1, crag)
        cell = view[y0:y1, x0:x1]
        cell[cast & ~body] *= 0.65
        base = (rock[0] * 0.9 if crag else rock[1]) * rng.uniform(0.85, 1.05)
        light = np.clip(1 + 0.4 * (-(xx - x) / rx - (yy - y) / ry) / 1.4, 0.55, 1.35)
        tone = base * light[..., None] + rng.integers(-8, 9, body.shape + (1,))
        cell[body] = tone[body]
        rim = body & ~_shape(xx, yy, x, y, rx, ry, crag, 2.5)
        cell[rim & ((xx - x) / rx + (yy - y) / ry < -0.3)] = cliff["lip"] * 0.9
        cell[body & ~_shape(xx, yy, x, y, rx, ry, crag, 1.2)] = cliff["foot"]
        for _ in range(rng.integers(1, 3)):
            cx = x + rng.integers(-rx // 2, rx // 2 + 1)
            top = y + rng.integers(-ry // 2, 0)
            length = rng.integers(ry // 2, ry + 1)
            for k in range(length):
                py, px = top + k, cx + (k // 3) * rng.choice([-1, 0, 1])
                if y0 <= py < y1 and x0 <= px < x1 and body[py - y0, px - x0]:
                    cell[py - y0, px - x0] = cliff["crack"]


def _pebbles(view: np.ndarray, inner: np.ndarray, dirt: np.ndarray, rock: np.ndarray, dials: dict, rng: np.random.Generator) -> None:
    ys, xs = np.nonzero(inner)
    for y, x in zip(ys[rng.random(len(ys)) < dials["pebble_density"]], xs[rng.random(len(ys)) < dials["pebble_density"]]):
        pw, ph = rng.integers(1, 4), rng.integers(1, 3)
        block = inner[y:y + ph, x:x + pw]
        view[y:y + ph, x:x + pw][block] = dirt[0] if rng.random() < 0.5 else dirt[2]
    for y, x in zip(ys[rng.random(len(ys)) < dials["slab_density"]], xs[rng.random(len(ys)) < dials["slab_density"]]):
        pw, ph = rng.integers(5, 10), rng.integers(3, 6)
        block = inner[y:y + ph, x:x + pw]
        ry, rx = np.mgrid[0:ph, 0:pw]
        stone = (((ry - ph / 2 + 0.5) / (ph / 2)) ** 2 + ((rx - pw / 2 + 0.5) / (pw / 2)) ** 2 <= 1)[:block.shape[0], :block.shape[1]] & block
        view[y:y + ph, x:x + pw][stone] = rock[1 + rng.integers(0, 2)]
        view[y:y + ph, x:x + pw][stone & ~np.roll(stone, -1, axis=0)] = rock[0]


def _paws(view: np.ndarray, data: dict, geo: Geometry, ink: np.ndarray, rng: np.random.Generator) -> None:
    """Paw prints pressed into the worn trails: a pad and four toes, in pairs, every so often along the way."""
    h, w = geo.shape
    for trail in data["trails"]:
        pts = spline(trail, 6)
        run = 0.0
        for a, b in zip(pts, pts[1:]):
            run += float(np.hypot(*(b - a)))
            if run < 70 + rng.integers(0, 50):
                continue
            run = 0.0
            heading = (b - a) / max(1e-6, float(np.hypot(*(b - a))))
            side = np.array([-heading[1], heading[0]])
            for k in (-1, 1):
                c = a + side * (5 * k) + heading * rng.integers(0, 8)
                cx, cy = int(c[0]), int(c[1])
                if not (2 <= cx < w - 3 and 3 <= cy < h - 2) or geo.trail[cy, cx] < 0.35:
                    continue
                view[cy:cy + 2, cx - 1:cx + 2] = ink
                for tx, ty in ((-2, -2), (-1, -3), (1, -3), (2, -2)):
                    view[cy + ty, cx + tx] = ink


def _rgb(text: str) -> np.ndarray:
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=int)


def check(rows: list, data: dict) -> list:
    """Cells a walker cannot reach from the start: every doorstep, the peak, and the far end of every trail."""
    w, h = data["size"]
    walk = {(x, y) for y in range(h) for x in range(w) if rows[y][x] in ".r-dP"}
    sx, sy = data["start"]
    seen, queue = {(sx, sy)}, deque([(sx, sy)])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in walk and (nx, ny) not in seen:
                seen.add((nx, ny))
                queue.append((nx, ny))
    wanted = [(home["at"][0] + HOME_W // 2, home["at"][1] + 1) for home in data["homes"]]
    wanted += [(int(t[-1][0]), int(t[-1][1])) for t in data["trails"]]
    return [c for c in wanted if 0 <= c[0] < w and 0 <= c[1] < h and c not in seen]


def main() -> None:
    data = load()
    rows = layout(Geometry(data))
    if "--print" in sys.argv:
        w, h = data["size"]
        print("    " + "".join(str(x % 10) for x in range(w)))
        for y in range(h):
            print(f"{y:3d} " + rows[y])
    unreachable = check(rows, data)
    if unreachable:
        print("unreachable:", unreachable)
    path = ROOT / "data" / "maps" / f"{data['map']}.txt"
    path.write_text("\n".join(rows) + "\n")
    meta_path = path.with_suffix(".json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"regions": {}}
    meta["regions"].setdefault(data["region"], {"name": "Fangridge Peaks", "race": "shifter", "kind": "mountain", "combat_zone": True, "tree": "pine", "dead_tree": "dead"})
    meta["regions"][data["region"]]["rect"] = [0, 0, data["size"][0], data["size"][1]]
    meta["buildings"] = {f"{home['at'][0]},{home['at'][1]}": "farmhouse" for home in data["homes"]}
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print("wrote", path.relative_to(ROOT), "and", meta_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
