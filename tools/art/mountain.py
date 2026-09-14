#!/usr/bin/env python3
"""The mountain map from data/mountain.json: a height field terraced into ledges, cliff pieces along every contour that
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
        self.props = json.loads((ROOT / "data" / "props.json").read_text())
        self.pieces = self._pieces(np.random.default_rng(data["seed"] + 7))
        self.stones = self._stones(np.random.default_rng(data["seed"] + 9))

    def _pieces(self, rng: np.random.Generator) -> list:
        """Cliff pieces as (name, x, y, flip): along every stretch of wall, a face per strip of columns with its lip on
        the wall's top, a second face stacked below it where the wall is tall, and a crumbling end where a stretch stops."""
        h, w = self.shape
        wall = (self.depth > 0) & ~(self.trail > 0.15)
        out, step = [], 58
        x = int(rng.integers(0, 24))
        prev = False
        while x < w:
            strip = wall[:, x:x + step]
            covered = strip.any(axis=0)
            if covered.mean() > 0.25:
                tops = np.array([np.argmax(strip[:, i]) for i in range(strip.shape[1]) if covered[i]])
                bottoms = np.array([h - 1 - np.argmax(strip[::-1, i]) for i in range(strip.shape[1]) if covered[i]])
                top, tall = int(np.median(tops)), float(np.median(bottoms - tops))
                left = x + int(np.argmax(covered)) - 8
                if not prev:
                    out.append(("cliff_end", left - 22, top - 2, True))
                if tall > 62:
                    out.append(("cliff_face", left - int(rng.integers(0, 6)), top + int(tall) - 56, bool(rng.random() < 0.5)))
                out.append(("cliff_face", left - int(rng.integers(0, 6)), top - 3, bool(rng.random() < 0.5)))
                prev = True
            else:
                if prev:
                    out.append(("cliff_end", x - 12, int(np.median([np.argmax(wall[:, i]) for i in range(max(0, x - 24), x) if wall[:, i].any()] or [0])) - 2, False))
                prev = False
            x += step
        return out

    def trail_solid(self) -> np.ndarray:
        return self.trail > 0.45

    def piece_mask(self) -> np.ndarray:
        """Opaque pixels of every placed cliff piece, so the cells they cover block."""
        mask = np.zeros(self.shape, dtype=bool)
        atlas = Image.open(ROOT / "assets" / "tiles" / "props.png").convert("RGBA")
        for name, x, y, flip in self.pieces:
            px, py, pw, ph = self.props[name]
            alpha = np.asarray(atlas.crop((px, py, px + pw, py + ph)))[..., 3] > 0
            if flip:
                alpha = alpha[:, ::-1]
            y0, x0 = max(0, y), max(0, x)
            y1, x1 = min(self.shape[0], y + ph), min(self.shape[1], x + pw)
            if y1 > y0 and x1 > x0:
                mask[y0:y1, x0:x1] |= alpha[y0 - y:y1 - y, x0 - x:x1 - x]
        return mask

    def _stones(self, rng: np.random.Generator) -> list:
        """Boulders and crags as (kind, cell x, cell y): dense in rubble, thickening across the apron toward the first
        wall, a few on every ledge, and a ring of crags around the peak; never on a trail, a wall, a home, or the start."""
        rates = self.data["boulders"]
        w, h = self.data["size"]
        peak = self.terrace == 4
        near_peak = np.zeros(self.shape, dtype=bool)
        for d in range(1, 40):
            near_peak[d:] |= peak[:-d] & ~peak[d:]
            near_peak[:-d] |= peak[d:] & ~peak[:-d]
            near_peak[:, d:] |= peak[:, :-d] & ~peak[:, d:]
            near_peak[:, :-d] |= peak[:, d:] & ~peak[:, :-d]
        blocked = (self.depth > 0) | self.trail_solid() | self.piece_mask()
        cells = {}
        taken = set()
        sx, sy = self.data["start"]
        for x in range(sx - 2, sx + 3):
            for y in range(sy - 2, sy + 3):
                taken.add((x, y))
        for home in self.data["homes"]:
            ax, ay = home["at"]
            for x in range(ax - 1, ax + HOME_W + 1):
                for y in range(ay - HOME_H - 4, ay + 2):
                    taken.add((x, y))
        for cy in range(h):
            for cx in range(w):
                sl = (slice(cy * TILE, (cy + 1) * TILE), slice(cx * TILE, (cx + 1) * TILE))
                if blocked[sl].any() or self.terrace[sl].max() != self.terrace[sl].min():
                    continue
                chance = rates["rubble"] if self.rubble[sl].mean() > 0.2 else 0.0
                chance += rates["apron"] * self.rockiness[sl].mean() ** 1.2
                chance += rates["ledge"] * (0.6 + 0.2 * self.terrace[sl].max()) if self.terrace[sl].max() > 0 else 0.0
                crag = near_peak[sl].mean() > 0.3
                chance += rates["crag"] if crag else 0.0
                if rng.random() >= chance:
                    continue
                kind = "crag" if crag else "boulder_large" if rng.random() < 0.15 + 0.2 * self.rockiness[sl].mean() else "boulder_medium" if rng.random() < 0.5 else "boulder_small"
                cells[(cx, cy)] = kind
        out = []
        for (cx, cy), kind in cells.items():
            span = [(cx + dx, cy + dy) for dx in range(3) for dy in range(2)] if kind == "boulder_large" else [(cx, cy)]
            if any(c in taken or c[0] >= w or c[1] >= h for c in span):
                continue
            if kind == "boulder_large" and any(blocked[y * TILE:(y + 1) * TILE, x * TILE:(x + 1) * TILE].any() for x, y in span):
                continue
            taken.update(span)
            out.append((kind, cx, cy))
        return out

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
    solid = (geo.depth > 0) | geo.rubble | geo.piece_mask()
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
    for kind, x, y in geo.stones:
        if kind == "boulder_large":
            for dx in range(3):
                for dy in range(2):
                    rows[y + dy][x + dx] = "X"
        else:
            rows[y][x] = {"boulder_small": "o", "boulder_medium": "O", "crag": "A"}[kind]
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
    view[wall] = (view * (0.85 - 0.3 * frac)[..., None])[wall]
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
    _place_pieces(view, geo)
    trail = geo.trail
    dirt_fill = _dirt_texture(geo.shape)
    rim = trail - np.minimum.reduce([np.roll(trail, s, a) for s in (-2, 2) for a in (0, 1)])
    dirt_fill[rim > 0.12] = dirt[0]
    alpha = np.clip(trail * 1.6 - 0.2, 0, 1)[..., None]
    view[...] = view * (1 - alpha) + dirt_fill * alpha
    inner = trail > 0.55
    steps = inner & wall & (geo.depth % 6 == 0)
    view[steps] = dirt[0]
    _paws(view, data, geo, dirt[0], rng)
    surface[trail > 0.4] = 4
    reach = np.clip((geo.height - data["snow_from"]) / 0.3, 0, 1)
    dust = (np.where(fbm(geo.shape, 22, rng, 2) > 0.3 - 0.55 * reach, 0.8, 0.0) * (reach > 0) * ~(wall & (geo.depth > 4)) * ~geo.piece_mask())[..., None]
    view[...] = view * (1 - dust) + snow * dust
    img[...] = np.clip(view, 0, 255).astype(np.uint8)
    return surface


def _place_pieces(view: np.ndarray, geo: Geometry) -> None:
    """Stamps the cliff pieces where the geometry placed them, each clipped to its own column's wall top so the lip
    stays on the contour while the foot spills onto the ground below."""
    atlas = Image.open(ROOT / "assets" / "tiles" / "props.png").convert("RGBA")
    wall = geo.depth > 0
    tops = np.where(wall.any(axis=0), np.argmax(wall, axis=0), 0)
    for name, x, y, flip in geo.pieces:
        px, py, pw, ph = geo.props[name]
        piece = np.asarray(atlas.crop((px, py, px + pw, py + ph))).astype(float)
        if flip:
            piece = piece[:, ::-1]
        y0, x0 = max(0, y), max(0, x)
        y1, x1 = min(geo.shape[0], y + ph), min(geo.shape[1], x + pw)
        if y1 <= y0 or x1 <= x0:
            continue
        cut = piece[y0 - y:y1 - y, x0 - x:x1 - x]
        rows = np.arange(y0, y1)[:, None]
        alpha = (cut[..., 3] / 255) * (rows >= tops[x0:x1][None, :] - 6)
        target = view[y0:y1, x0:x1]
        target[...] = target * (1 - alpha[..., None]) + cut[..., :3] * alpha[..., None]


def _dirt_texture(shape: tuple[int, int]) -> np.ndarray:
    """The dirt tileset's full tile repeated across the map."""
    atlas = Image.open(ROOT / "assets" / "tiles" / "grass_dirt_summer.png").convert("RGBA")
    tile = np.asarray(atlas.crop((3 * TILE, 3 * TILE, 4 * TILE, 4 * TILE))).astype(float)[..., :3]
    reps = (shape[0] // TILE + 1, shape[1] // TILE + 1, 1)
    return np.tile(tile, reps)[:shape[0], :shape[1]]


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
    for kind, x, y in Geometry(data).stones:
        if kind == "boulder_large":
            meta["buildings"][f"{x},{y + 1}"] = kind
    meta["palette"] = "fangridge"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print("wrote", path.relative_to(ROOT), "and", meta_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
