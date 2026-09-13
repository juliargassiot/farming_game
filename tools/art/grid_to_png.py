"""Converts string-grid files under tools/art/grids/ into PNGs. Directives: @out path, @at col row, @scale n, @<char> #rrggbb|none."""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
GRIDS = ROOT / "tools" / "art" / "grids"


def parse(path: Path) -> dict:
    palette, rows, meta = {}, [], {"at": (0, 0), "scale": 1, "out": None}
    for raw in path.read_text().splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("@"):
            key, _, value = line[1:].partition(" ")
            value = value.strip()
            if key == "out":
                meta["out"] = value
            elif key == "at":
                meta["at"] = tuple(int(v) for v in value.split())
            elif key == "scale":
                meta["scale"] = int(value)
            elif len(key) == 1:
                palette[key] = None if value == "none" else tuple(int(value[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
            continue
        rows.append(line)
    widths = {len(r) for r in rows}
    if len(widths) != 1 or not meta["out"]:
        raise SystemExit(f"{path}: rows must share one width and @out is required")
    meta.update(palette=palette, rows=rows, width=widths.pop(), height=len(rows), path=path)
    return meta


def render(grid: dict) -> Image.Image:
    img = Image.new("RGBA", (grid["width"], grid["height"]), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(grid["rows"]):
        for x, ch in enumerate(row):
            if ch not in grid["palette"]:
                raise SystemExit(f"{grid['path']}: '{ch}' has no @{ch} palette entry")
            color = grid["palette"][ch]
            if color:
                px[x, y] = color
    return img


def convert_all() -> list[Path]:
    by_out: dict[str, list[dict]] = {}
    for path in sorted(GRIDS.rglob("*.grid")):
        grid = parse(path)
        by_out.setdefault(grid["out"], []).append(grid)
    written = []
    for out, grids in by_out.items():
        w = max((g["at"][0] + 1) * g["width"] for g in grids)
        h = max((g["at"][1] + 1) * g["height"] for g in grids)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for g in grids:
            canvas.paste(render(g), (g["at"][0] * g["width"], g["at"][1] * g["height"]))
        scale = grids[0]["scale"]
        if scale > 1:
            canvas = canvas.resize((w * scale, h * scale), Image.NEAREST)
        target = ROOT / out
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target)
        written.append(target)
    return written


if __name__ == "__main__":
    for target in convert_all():
        print(target.relative_to(ROOT))
    sys.exit(0)
