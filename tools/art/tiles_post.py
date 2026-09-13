"""Post-processing for generated Wang tilesets: seam fading, furrow softening, and a demo field for previews."""
import numpy as np
from PIL import Image

DEMO_CORNERS = ["0000000000", "0011111000", "0111111100", "0111111100", "0011111100", "0000011000", "0000000000"]


def mean_colour(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGBA")).astype(float)[..., :3].reshape(-1, 3).mean(axis=0)


def _classify(rgb: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    return np.linalg.norm(rgb - lower, axis=-1) < np.linalg.norm(rgb - upper, axis=-1)


def edge_blend(tiles: dict, lower: np.ndarray, upper: np.ndarray, width: int, strength: float = 0.85) -> dict:
    """Fade the outer `width` pixels of every tile toward its terrain's flat colour so neighbours meet without seams."""
    if not width:
        return tiles
    size = next(iter(tiles.values())).width
    yy, xx = np.mgrid[0:size, 0:size]
    dist = np.minimum(np.minimum(xx, size - 1 - xx), np.minimum(yy, size - 1 - yy))
    w = (np.clip(1 - dist / width, 0, 1) * strength)[..., None]
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        flat = np.where(_classify(a[..., :3], lower, upper)[..., None], lower, upper)
        a[..., :3] = a[..., :3] * (1 - w) + flat * w
        out[key] = Image.fromarray(a.round().astype(np.uint8), "RGBA")
    return out


def soften(tiles: dict, lower: np.ndarray, upper: np.ndarray, amount: float) -> dict:
    """Pull upper-terrain pixels toward their mean colour so furrows read softer."""
    if not amount:
        return tiles
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        is_upper = ~_classify(a[..., :3], lower, upper)
        a[..., :3] = np.where(is_upper[..., None], a[..., :3] * (1 - amount) + upper * amount, a[..., :3])
        out[key] = Image.fromarray(a.round().astype(np.uint8), "RGBA")
    return out


def finish(tiles: dict, variants: list, spec: dict) -> tuple[dict, list]:
    lower, upper = mean_colour(tiles[0]), mean_colour(tiles[15])
    width, amount = spec.get("edge_blend", 0), spec.get("soften_upper", 0.0)
    done = soften(edge_blend(tiles, lower, upper, width), lower, upper, amount)
    done_variants = [edge_blend({0: v}, lower, upper, width)[0] for v in variants]
    return done, done_variants


def demo_field(tiles: dict, variants: list, size: int, seed: int = 3) -> Image.Image:
    import random
    rng = random.Random(seed)
    rows, cols = len(DEMO_CORNERS) - 1, len(DEMO_CORNERS[0]) - 1
    img = Image.new("RGBA", (cols * size, rows * size))
    for y in range(rows):
        for x in range(cols):
            corners = [int(DEMO_CORNERS[y + dy][x + dx]) for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))]
            idx = (corners[0] << 3) | (corners[1] << 2) | (corners[2] << 1) | corners[3]
            tile = rng.choice(variants) if idx == 0 and variants and rng.random() < 0.35 else tiles[idx]
            img.alpha_composite(tile, (x * size, y * size))
    return img
