#!/usr/bin/env python3
"""Writes the overworld hub and the witch, vampire and mermaid districts: data/maps/<name>.txt and the regions,
buildings and edge exits in each .json. The mountain (fangridge) is drawn by tools/art/mountain.py instead.
Run `layout.py` after changing a layout below, then `tools/art/grass_paint.py --map <name>` for each map touched."""
import json
import math
import random
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROPS = json.loads((ROOT / "data/props.json").read_text())
SOLID = set("~#BbwM%tTH^RXoOA")
HUB = (120, 84)
DISTRICT = (120, 90)


class Grid:
    def __init__(self, width: int, height: int, fill: str = ".") -> None:
        self.w, self.h = width, height
        self.g = [[fill] * width for _ in range(height)]
        self.buildings: dict[str, str] = {}
        self.rnd = random.Random(7)

    def put(self, x: int, y: int, ch: str) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def get(self, x: int, y: int) -> str:
        return self.g[y][x] if 0 <= x < self.w and 0 <= y < self.h else ""

    def rect(self, x0: int, y0: int, x1: int, y1: int, ch: str) -> None:
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.put(x, y, ch)

    def noise(self, seed: int, scale: float = 6.0):
        r = random.Random(seed)
        gw, gh = int(self.w / scale) + 4, int(self.h / scale) + 4
        lat = [[r.random() for _ in range(gw)] for _ in range(gh)]

        def at(x: float, y: float) -> float:
            fx, fy = max(0, x) / scale, max(0, y) / scale
            ix, iy = int(fx), int(fy)
            tx, ty = fx - ix, fy - iy
            tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
            a = lat[iy][ix] * (1 - tx) + lat[iy][ix + 1] * tx
            b = lat[iy + 1][ix] * (1 - tx) + lat[iy + 1][ix + 1] * tx
            return a * (1 - ty) + b * ty
        return at

    def blob(self, cx: float, cy: float, rx: float, ry: float, ch: str, seed: int, rough: float = 0.35, on: str | None = None) -> None:
        n = self.noise(seed, 4.0)
        for y in range(int(cy - ry - 3), int(cy + ry + 4)):
            for x in range(int(cx - rx - 3), int(cx + rx + 4)):
                d = math.hypot((x - cx) / rx, (y - cy) / ry)
                if d + (n(x, y) - 0.5) * rough * 2 < 1.0 and (on is None or (self.get(x, y) and self.get(x, y) in on)):
                    self.put(x, y, ch)

    def fill_noise(self, x0: int, y0: int, x1: int, y1: int, ch: str, seed: int, above: float, scale: float = 4.0, on: str = ".") -> None:
        n = self.noise(seed, scale)
        for y in range(y0, y1):
            for x in range(x0, x1):
                if self.get(x, y) and self.get(x, y) in on and n(x, y) > above:
                    self.put(x, y, ch)

    def scatter(self, x0: int, y0: int, x1: int, y1: int, ch: str, count: int, seed: int, on: str = ".", gap: int = 0) -> None:
        r = random.Random(seed)
        placed = 0
        for _ in range(count * 30):
            if placed >= count:
                break
            x, y = r.randrange(x0, x1), r.randrange(y0, y1)
            clear = all(self.get(x + dx, y + dy) != "" and self.get(x + dx, y + dy) in on for dy in range(-gap, gap + 1) for dx in range(-gap, gap + 1))
            if clear:
                self.put(x, y, ch)
                placed += 1

    def path(self, points: list[tuple[int, int]], ch: str = "=", over: str = ".\",:+=-") -> None:
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            x, y = x0, y0
            if self.get(x, y) in over:
                self.put(x, y, ch)
            while (x, y) != (x1, y1):
                if x != x1 and (y == y1 or self.rnd.random() < 0.5):
                    x += 1 if x1 > x else -1
                else:
                    y += 1 if y1 > y else -1
                if self.get(x, y) and self.get(x, y) in over:
                    self.put(x, y, ch)

    def building(self, x: int, y: int, prop: str, door_dx: int | None = None, sleep: bool = False, door: bool = True) -> tuple[int, int]:
        """A sprite building: solid footprint sized to the sprite, anchored at its bottom-left, the door in the bottom row."""
        w, h = -(-PROPS[prop][2] // 32), -(-PROPS[prop][3] // 32)
        self.rect(x, y, x + w, y + h, "X")
        self.buildings[f"{x},{y + h - 1}"] = prop
        dx = x + (w // 2 if door_dx is None else door_dx)
        if door:
            self.put(dx, y + h - 1, "B" if sleep else "d")
        return dx, y + h

    def home(self, x: int, y: int) -> tuple[int, int]:
        """A stand-in home until each race has its own; returns the cell below the door."""
        dx, below = self.building(x, y, "farmhouse")
        return dx, below

    def reachable(self, start: tuple[int, int]) -> set:
        seen, q = {start}, deque([start])
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < self.w and 0 <= n[1] < self.h and n not in seen and self.g[n[1]][n[0]] not in SOLID:
                    seen.add(n)
                    q.append(n)
        return seen

    def write(self, name: str, meta: dict) -> None:
        text = "\n".join("".join(r) for r in self.g) + "\n"
        (ROOT / "data/maps" / f"{name}.txt").write_text(text)
        meta["buildings"] = dict(sorted(self.buildings.items(), key=lambda kv: tuple(int(v) for v in kv[0].split(","))[::-1]))
        regions = list(meta["regions"].items())
        lines = ["{"] + [f'  "{k}": {json.dumps(v)},' for k, v in meta.items() if k not in ("regions", "buildings", "exits")]
        lines += ['  "regions": {'] + [f'    "{k}": {json.dumps(v)}' + ("," if i < len(regions) - 1 else "") for i, (k, v) in enumerate(regions)] + ["  },"]
        exits = {f"{x},{y}": {"map": e["map"], "at": "%d,%d" % tuple(e["arrive"]), "facing": e["facing"]} for e in meta["exits"] for y in range(e["rect"][1], e["rect"][3]) for x in range(e["rect"][0], e["rect"][2])}
        lines += ['  "exits": {'] + [f'    "{k}": {json.dumps(v)}' + ("," if i < len(exits) - 1 else "") for i, (k, v) in enumerate(exits.items())] + ["  },"]
        items = list(meta["buildings"].items())
        lines += ['  "buildings": {'] + [f'    "{k}": "{v}"' + ("," if i < len(items) - 1 else "") for i, (k, v) in enumerate(items)] + ["  }", "}"]
        (ROOT / "data/maps" / f"{name}.json").write_text("\n".join(lines) + "\n")
        start = next(((x, y) for y in range(self.h) for x in range(self.w) if self.g[y][x] == "P"), None)
        seen = self.reachable(start) if start else set()
        for k, region in meta["regions"].items():
            x0, y0, x1, y1 = region["rect"]
            cells = [(x, y) for y in range(y0, y1) for x in range(x0, x1) if self.g[y][x] not in SOLID]
            print(f"{name:10s} {k:12s} walkable {len(cells):5d} reachable {sum(1 for c in cells if c in seen):5d}")
        for e in meta["exits"]:
            x0, y0, x1, y1 = e["rect"]
            ok = all((x, y) in seen for y in range(y0, y1) for x in range(x0, x1))
            print(f"{name:10s} exit to {e['map']:10s} {'reachable' if ok else 'CUT OFF'}")


def region(name: str, race: str, kind: str, rect: list, tree: str, combat: bool = False) -> dict:
    return {"name": name, "race": race, "kind": kind, "rect": rect, "combat_zone": combat, "tree": tree, "dead_tree": "dead"}


def fence(g: Grid, x0: int, y0: int, x1: int, y1: int) -> None:
    for x in range(x0, x1):
        g.put(x, y0, "#")
        g.put(x, y1 - 1, "#")
    for y in range(y0, y1):
        g.put(x0, y, "#")
        g.put(x1 - 1, y, "#")


def sand_ring(g: Grid, width: int = 2) -> None:
    for y in range(g.h):
        for x in range(g.w):
            if g.g[y][x] == "w":
                for dy in range(-width, width + 1):
                    for dx in range(-width, width + 1):
                        if g.get(x + dx, y + dy) in (".", '"'):
                            g.put(x + dx, y + dy, ",")


def hub() -> None:
    g = Grid(*HUB)
    # Wistmoor Square: a loose town around the fountain plaza, shops six to ten tiles apart
    g.rect(54, 28, 78, 44, "+")
    g.building(62, 31, "fountain", door=False)
    shops = [
        ((44, 18), "shop_townhall", None), ((56, 21), "shop_general", None), ((72, 18), "shop_tavern", None),
        ((40, 28), "shop_bakery", 2), ((40, 38), "shop_clinic", None), ((40, 48), "shop_magic", 5),
        ((82, 28), "shop_smithy", None), ((84, 38), "shop_tailor", 3), ((52, 48), "shop_inn", None), ((72, 48), "shop_salon", None),
    ]
    doors = [g.building(x, y, prop, door_dx=dx) for (x, y), prop, dx in shops]
    g.path([(66, 28), (66, 12), (60, 12), (60, 0)])
    g.path([(61, 12), (61, 1)])
    g.path([(54, 36), (0, 36)])
    g.path([(54, 37), (0, 37)])
    g.path([(78, 36), (119, 36)])
    g.path([(78, 37), (119, 37)])
    g.path([(66, 44), (66, 58), (50, 58), (50, 62)])
    g.path([(67, 44), (67, 58)])
    for dx, below in doors:
        target = min([(66, below), (54, 36), (78, 36), (66, 28), (66, 44)], key=lambda p: abs(p[0] - dx) + abs(p[1] - below))
        g.path([(dx, below), (dx, target[1]) if abs(target[1] - below) < abs(target[0] - dx) else (target[0], below), target])
    g.scatter(32, 12, 100, 60, "T", 40, 71, gap=2)
    g.fill_noise(32, 12, 100, 60, '"', 72, 0.62)
    # Wistmoor Commons: open meadow along the north edge with the road to the witches' prairie
    g.fill_noise(0, 0, 120, 12, '"', 11, 0.55)
    g.scatter(0, 0, 120, 12, "T", 18, 12, gap=1)
    g.blob(96, 6, 5, 2.5, "~", 13, rough=0.3)
    # Gravehollow: the ghosts' graveyard just west of town, dead trees along the road to the vampires' crags
    fence(g, 10, 14, 30, 33)
    g.rect(11, 15, 29, 32, ".")
    for y in range(18, 31, 3):
        for x in range(13, 28, 3):
            g.put(x, y, "o")
    g.building(16, 15, "farmhouse", door_dx=4)
    g.put(20, 32, "=")
    g.path([(20, 33), (20, 36)])
    g.scatter(0, 12, 32, 60, "t", 34, 35, gap=1)
    g.fill_noise(0, 40, 32, 60, ":", 36, 0.6)
    g.blob(8, 50, 5, 3, "%", 37, rough=0.4)
    # Deepgloom Mine: rocky ground east of town, its mouth up a spur off the road to the mountain
    g.blob(110, 22, 9, 8, "^", 81, rough=0.35)
    g.blob(104, 50, 8, 6, "^", 82, rough=0.35)
    g.rect(106, 20, 114, 28, "c")
    g.rect(109, 18, 111, 20, "m")
    g.path([(110, 36), (110, 28)], over=".\"^c")
    g.scatter(100, 12, 120, 60, "o", 8, 83, gap=1)
    g.scatter(100, 12, 120, 60, "T", 8, 84, gap=1)
    # Hollow Wood: oak forest south-west for foraging and chopping
    g.fill_noise(0, 60, 32, 84, "T", 91, 0.56, scale=3.0)
    g.scatter(0, 60, 32, 84, "T", 30, 92, gap=1)
    g.blob(10, 72, 4, 2.5, "~", 93, rough=0.3)
    g.path([(34, 70), (22, 70), (12, 78)], over=".T")
    # Hollowbrook Farm
    g.rect(32, 60, 68, 84, ".")
    fence(g, 34, 62, 67, 83)
    g.building(36, 64, "farmhouse", sleep=True)
    g.rect(46, 72, 63, 80, "s")
    g.blob(58, 66, 3, 1.6, "~", 94, rough=0.2)
    g.put(50, 62, "=")
    g.put(34, 70, "=")
    g.put(66, 72, "=")
    g.put(44, 70, "P")
    # Saltwhisper Shore: the beach south of town where the coast path leaves for the mermaids' cove
    coast = g.noise(21, 9.0)
    for x in range(68, 120):
        top = 78 + int((coast(x, 0) - 0.5) * 4) - (x - 90) // 8
        for y in range(max(top, 70), 84):
            g.put(x, y, "w")
    g.rect(80, 70, 90, 84, ".")
    sand_ring(g, 3)
    for y in range(66, 84):
        for x in range(68, 120):
            if g.get(x, y) == "." and any(g.get(x + dx, y + dy) == "," for dy in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2)):
                g.put(x, y, ",")
    g.rect(80, 76, 90, 84, ",")
    g.path([(67, 72), (84, 72), (84, 83)], over=".\",")
    g.path([(85, 72), (85, 83)], over=".\",")
    g.scatter(68, 60, 120, 76, "T", 10, 95, on=".,", gap=1)
    g.scatter(68, 60, 120, 84, "o", 6, 96, on=",", gap=1)
    meta = {
        "town": "Wistmoor",
        "regions": {
            "commons": region("Wistmoor Commons", "", "meadow", [0, 0, 120, 12], "oak"),
            "gravehollow": region("Gravehollow", "ghost", "graveyard", [0, 12, 32, 60], "dead"),
            "square": region("Wistmoor Square", "", "town", [32, 12, 100, 60], "oak"),
            "deepgloom": region("Deepgloom Mine", "", "mine", [100, 12, 120, 60], "oak", True),
            "hollowwood": region("Hollow Wood", "", "forest", [0, 60, 32, 84], "oak"),
            "farm": region("Hollowbrook Farm", "", "farm", [32, 60, 68, 84], "oak"),
            "shore": region("Saltwhisper Shore", "", "beach", [68, 60, 120, 84], "oak"),
        },
        "exits": [
            {"rect": [59, 0, 63, 1], "map": "hexmeadow", "arrive": [60, 88], "facing": "north"},
            {"rect": [119, 35, 120, 39], "map": "fangridge", "arrive": [6, 54], "facing": "north"},
            {"rect": [0, 35, 1, 39], "map": "duskspire", "arrive": [118, 45], "facing": "west"},
            {"rect": [83, 83, 87, 84], "map": "pearlwater", "arrive": [60, 1], "facing": "south"},
        ],
    }
    g.write("world", meta)


def hexmeadow() -> None:
    """The witches' prairie north of town: entered from its south edge."""
    g = Grid(*DISTRICT)
    g.fill_noise(0, 0, 120, 90, '"', 61, 0.5)
    g.blob(30, 40, 9, 5, "~", 62, rough=0.3)
    g.blob(95, 70, 6, 4, "~", 63, rough=0.3)
    homes = [(20, 18), (86, 14), (14, 62), (92, 48)]
    doors = [g.home(x, y) for x, y in homes]
    for a in range(10):
        g.put(60 + int(round(6 * math.cos(a * math.pi / 5))), 30 + int(round(4 * math.sin(a * math.pi / 5))), "o")
    g.put(60, 30, "O")
    g.path([(60, 89), (60, 40), (60, 36)], over=".\"")
    g.path([(61, 89), (61, 40)], over=".\"")
    for dx, below in doors:
        g.path([(dx, below), (dx, 42) if below < 42 else (dx, below), (60, 42)], over=".\"")
    g.scatter(0, 0, 120, 90, "T", 120, 64, on='."', gap=2)
    g.scatter(0, 0, 120, 90, "t", 6, 65, on='."', gap=2)
    g.put(60, 88, "P")
    meta = {
        "regions": {"hexmeadow": region("Hexmeadow", "witch", "prairie", [0, 0, 120, 90], "willow", True)},
        "exits": [{"rect": [58, 89, 64, 90], "map": "world", "arrive": [60, 1], "facing": "south"}],
    }
    g.write("hexmeadow", meta)


def duskspire() -> None:
    """The vampires' crags west of town: entered from its east edge, homes cut into the cliffs."""
    g = Grid(*DISTRICT)
    g.blob(30, 14, 34, 12, "M", 51, rough=0.35)
    g.blob(90, 12, 26, 10, "M", 52, rough=0.35)
    g.blob(14, 60, 14, 22, "M", 53, rough=0.35)
    g.blob(70, 80, 40, 8, "M", 54, rough=0.35)
    g.blob(50, 50, 8, 6, "~", 55, rough=0.3)
    homes = [(38, 26), (84, 22), (30, 62), (74, 60)]
    doors = [g.home(x, y) for x, y in homes]
    for x, y in homes:
        g.rect(x - 1, y - 3, x + 9, y, "c")
    g.path([(119, 45), (100, 45), (60, 45)], over=".\"c")
    g.path([(119, 46), (100, 46)], over=".\"c")
    for dx, below in doors:
        g.path([(dx, below), (dx, 45), (60, 45)], over=".\"c")
    g.scatter(0, 0, 120, 90, "T", 90, 56, on=".", gap=2)
    g.scatter(0, 0, 120, 90, "t", 12, 57, on=".", gap=2)
    g.scatter(0, 0, 120, 90, "o", 20, 58, on=".", gap=1)
    g.put(118, 45, "P")
    meta = {
        "regions": {"duskspire": region("Duskspire Crags", "vampire", "cave", [0, 0, 120, 90], "thorn", True)},
        "exits": [{"rect": [119, 43, 120, 48], "map": "world", "arrive": [1, 36], "facing": "east"}],
    }
    g.write("duskspire", meta)


def pearlwater() -> None:
    """The mermaids' cove south of town: entered from its north edge, the fishmonger's cave just inside."""
    g = Grid(*DISTRICT)
    g.rect(0, 14, 120, 90, ",")
    coast = g.noise(21, 9.0)
    for x in range(120):
        top = 58 + int((coast(x, 0) - 0.5) * 8) + abs(x - 60) // 6
        for y in range(top, 90):
            g.put(x, y, "w")
    g.blob(60, 66, 22, 12, "w", 22, rough=0.25)
    g.blob(30, 50, 10, 6, "w", 23, rough=0.3)
    sand_ring(g, 3)
    g.building(50, 8, "shop_fishmonger")
    homes = [(14, 22), (96, 20), (10, 46), (100, 56)]
    doors = [g.home(x, y) for x, y in homes]
    g.path([(60, 0), (60, 14), (60, 40)], over='.",')
    g.path([(61, 0), (61, 14)], over='.",')
    for dx, below in doors:
        g.path([(dx, below), (dx, 40), (60, 40)], over='.",')
    for x in range(58, 64):
        g.put(x, 54, "D")
        g.put(x, 55, "D")
    for y in range(55, 64):
        g.put(60, y, "D")
        g.put(61, y, "D")
    for (x, y) in [(20, 80), (24, 82), (90, 76), (108, 84), (44, 86)]:
        g.put(x, y, "^")
    g.scatter(0, 14, 120, 90, "T", 60, 94, on=",", gap=2)
    g.scatter(0, 0, 120, 14, "T", 8, 95, on=".", gap=1)
    g.scatter(0, 14, 120, 90, "o", 12, 96, on=",", gap=1)
    g.put(60, 1, "P")
    meta = {
        "regions": {"pearlwater": region("Pearlwater Cove", "mermaid", "coast", [0, 0, 120, 90], "coconut", True)},
        "exits": [{"rect": [58, 0, 64, 1], "map": "world", "arrive": [84, 82], "facing": "north"}],
    }
    g.write("pearlwater", meta)


if __name__ == "__main__":
    hub()
    hexmeadow()
    duskspire()
    pearlwater()
