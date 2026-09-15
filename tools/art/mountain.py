#!/usr/bin/env python3
"""The mountain map's cells, read straight from the hand-drawn mockup that its panels are painted from: ridges and
everything beyond the mountain's outline block, green is grass, the black line is the trail, the unpainted inside is bare
rock, purple outlines become home footprints with a door, and the cave and lookout are marked. The trail runs on from
its lowest cell to the bottom edge, where the farmer starts and where stepping off leads back to the overworld trailhead.
Run `mountain.py` to rewrite data/maps/fangridge.txt and the homes and exits in its .json."""
import json
from pathlib import Path

import numpy as np
from PIL import Image

import panels

ROOT = Path(__file__).resolve().parents[2]
TILE = 32
MAP = "fangridge"
SYMBOLS = {"void": "^", "ridge": "^", "grass": ".", "path": "-", "home": "X", "dig": "r", "cave": "^", "lookout": "r"}
TRAILHEAD = {"map": "world", "at": "24,19", "facing": "south"}


def kinds_per_cell() -> np.ndarray:
    """The mockup at map scale, one KINDS index per pixel, with the unpainted inside of the mountain as bare rock (index -1)."""
    mock = Image.open(panels.MOCKUP).resize((panels.MAP_WIDTH, panels.MAP_HEIGHT), Image.NEAREST)
    kinds = panels.classify(mock)
    kinds[(kinds == 0) & panels._inside_mountain(kinds)] = -1
    return kinds


def layout() -> tuple[list, dict]:
    kinds = kinds_per_cell()
    names = list(panels.KINDS)
    w, h = panels.MAP_WIDTH // TILE, panels.MAP_HEIGHT // TILE
    rows = [["r"] * w for _ in range(h)]
    path_index, home_index = names.index("path"), names.index("home")
    for y in range(h):
        for x in range(w):
            cell = kinds[y * TILE:(y + 1) * TILE, x * TILE:(x + 1) * TILE]
            if (cell == path_index).mean() >= 0.2:
                rows[y][x] = "-"
                continue
            counts = np.bincount(cell[cell >= 0].ravel(), minlength=len(names)) if (cell >= 0).any() else np.zeros(len(names))
            if counts.sum() < cell.size * 0.5:
                rows[y][x] = "r"
            else:
                rows[y][x] = SYMBOLS[names[int(counts.argmax())]]
    buildings = {}
    for x0, y0, x1, y1 in _components(kinds == home_index):
        cx0, cy0, cx1, cy1 = x0 // TILE, y0 // TILE, x1 // TILE, y1 // TILE
        for y in range(cy0, cy1 + 1):
            for x in range(cx0, cx1 + 1):
                rows[y][x] = "X"
        rows[cy1][(cx0 + cx1) // 2] = "d"
        buildings[f"{cx0},{cy1}"] = "farmhouse"
    trail = [(x, y) for y in range(h) for x in range(w) if rows[y][x] == "-"]
    sx, sy = max(trail, key=lambda c: c[1])
    for y in range(sy, h):
        rows[y][sx] = rows[y][sx + 1] = "-"
    rows[h - 2][sx] = "P"
    exits = {f"{sx},{h - 1}": TRAILHEAD, f"{sx + 1},{h - 1}": TRAILHEAD}
    return ["".join(r) for r in rows], buildings, exits


def _components(mask: np.ndarray) -> list:
    """Bounding boxes of separate blobs, found by flooding from every unvisited pixel on a coarse grid."""
    coarse = mask[::8, ::8]
    seen = np.zeros_like(coarse)
    boxes = []
    for y, x in zip(*np.nonzero(coarse)):
        if seen[y, x]:
            continue
        stack, pts = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            pts.append((cy, cx))
            for ny in range(max(0, cy - 2), min(coarse.shape[0], cy + 3)):
                for nx in range(max(0, cx - 2), min(coarse.shape[1], cx + 3)):
                    if coarse[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        ys, xs = zip(*pts)
        boxes.append((min(xs) * 8, min(ys) * 8, max(xs) * 8 + 7, max(ys) * 8 + 7))
    return boxes


def main() -> None:
    rows, buildings, exits = layout()
    path = ROOT / "data" / "maps" / f"{MAP}.txt"
    path.write_text("\n".join(rows) + "\n")
    meta_path = path.with_suffix(".json")
    meta = json.loads(meta_path.read_text())
    meta["buildings"] = buildings
    meta["exits"] = exits
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print("wrote", path.relative_to(ROOT), "with", len(buildings), "homes")


if __name__ == "__main__":
    main()
