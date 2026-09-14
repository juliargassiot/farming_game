"""Post-processing for generated Wang tilesets: seam fading, furrow softening, soil cutouts, and a demo field for previews."""
import numpy as np
from PIL import Image

DEMO_CORNERS = ["0000000000", "0011111000", "0111111100", "0111111100", "0011111100", "0000011000", "0000000000"]
DEMO_TILLED = ["0000000000", "0000000000", "0011110000", "0011110000", "0001110000", "0000000000", "0000000000"]


def mean_colour(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGBA")).astype(float)[..., :3].reshape(-1, 3).mean(axis=0)


def _classify(rgb: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    return np.linalg.norm(rgb - lower, axis=-1) < np.linalg.norm(rgb - upper, axis=-1)


def _image(a: np.ndarray) -> Image.Image:
    return Image.fromarray(a.round().astype(np.uint8), "RGBA")


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
        out[key] = _image(a)
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
        out[key] = _image(a)
    return out


def finish(tiles: dict, spec: dict) -> dict:
    lower, upper = mean_colour(tiles[0]), mean_colour(tiles[15])
    return soften(edge_blend(tiles, lower, upper, spec.get("edge_blend", 0)), lower, upper, spec.get("soften_upper", 0.0))


def demo_field(tiles: dict, size: int, mark: list | None = None) -> Image.Image:
    """Tiles laid by a corner-mask grid, transparent wherever no corner is marked."""
    mark = mark or DEMO_CORNERS
    rows, cols = len(mark) - 1, len(mark[0]) - 1
    img = Image.new("RGBA", (cols * size, rows * size))
    for y in range(rows):
        for x in range(cols):
            corners = [int(mark[y + dy][x + dx]) for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))]
            idx = (corners[0] << 3) | (corners[1] << 2) | (corners[2] << 1) | corners[3]
            if idx:
                img.alpha_composite(tiles[idx], (x * size, y * size))
    return img


def hex_colour(text: str) -> np.ndarray:
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def recolour(tiles: dict, lower: np.ndarray, upper: np.ndarray, upper_target: np.ndarray, flatten: float = 0.0) -> dict:
    """Flatten the upper terrain toward its mean, then shift it so the mean lands on the target colour."""
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        rgb = a[..., :3]
        is_lower = _classify(rgb, lower, upper)[..., None]
        shifted = rgb * (1 - flatten) + upper * flatten + (upper_target - upper)
        a[..., :3] = np.clip(np.where(is_lower, rgb, shifted), 0, 255)
        out[key] = _image(a)
    return out


def cutout(tiles: dict, lower: np.ndarray, upper: np.ndarray, classify_from: dict | None = None) -> dict:
    """Keep only upper-terrain pixels, judged on `classify_from` (default: the tiles themselves), so the tile overlays the painted ground."""
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        source = np.asarray((classify_from or tiles)[key].convert("RGBA")).astype(float)
        a[..., 3] = np.where(_classify(source[..., :3], lower, upper), 0, 255)
        out[key] = _image(a)
    return out


def tint(tiles: dict, factor: np.ndarray) -> dict:
    """Multiply every pixel by a colour factor (0-1 per channel); alpha is kept."""
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        a[..., :3] = np.clip(a[..., :3] * factor, 0, 255)
        out[key] = _image(a)
    return out
