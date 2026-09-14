"""Every crop's seed bag: the hand-drawn tan sack from grids/items/seed_bag.grid with one seed on the front in that crop's seed colour."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from grid_to_png import parse, render
from sheets import labelled_grid

ART = Path(__file__).resolve().parent
ROOT = ART.parents[1]
SEED = [".dddd.", "dmmlld", "dmmmmd", "ddmmdd", ".dddd."]
SEED_AT = (13, 16)


def seed_colour(seed: Image.Image) -> tuple[int, int, int]:
    """Median of the brightest fifth of the seed stage, which is the seeds themselves rather than the mound."""
    a = np.asarray(seed.convert("RGBA")).astype(int)
    alpha = a[..., 3] > 0
    luma = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    picked = alpha & (luma >= np.percentile(luma[alpha], 80))
    return tuple(int(v) for v in np.median(a[..., :3][picked], axis=0))


def _scale(colour: tuple[int, int, int], k: float) -> tuple[int, int, int, int]:
    return (*(int(max(0, min(255, v * k))) for v in colour), 255)


def build(seed: Image.Image) -> Image.Image:
    bag = render(parse(ART / "grids" / "items" / "seed_bag.grid"))
    colour = seed_colour(seed)
    inks = {"d": _scale(colour, 0.5), "m": _scale(colour, 1.0), "l": _scale(colour, 1.4)}
    px = bag.load()
    for j, row in enumerate(SEED):
        for i, ch in enumerate(row):
            if ch != ".":
                px[SEED_AT[0] + i, SEED_AT[1] + j] = inks[ch]
    return bag


def main() -> None:
    sys.path.insert(0, str(ART))
    from art import now, rel, save_generated, sha

    generated = json.loads((ART / "generated.json").read_text())
    items = []
    for name, record in generated["crops"].items():
        folder = ART / "raw" / "crops" / name
        if not (folder / "seed.png").exists():
            continue
        out = folder / "bag.png"
        build(Image.open(folder / "seed.png")).save(out)
        record["stages"]["bag"] = {"file": rel(out), "created": now(), "hash": sha(out), "edit": "tan sack grid with one seed in the seed-stage colour"}
        items.append((name, Image.open(out).convert("RGBA")))
    save_generated(generated)
    preview = ROOT / "previews" / "art" / "crops-bag.png"
    labelled_grid(items).save(preview)
    print(preview)


if __name__ == "__main__":
    main()
