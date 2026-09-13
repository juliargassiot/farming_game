"""Post-processing for generated Wang tilesets: seam fading, furrow softening, and a demo field for previews."""
import numpy as np
from PIL import Image

DEMO_CORNERS = ["0000000000", "0011111000", "0111111100", "0111111100", "0011111100", "0000011000", "0000000000"]
DEMO_TILLED = ["0000000000", "0000000000", "0011110000", "0011110000", "0001110000", "0000000000", "0000000000"]


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


def demo_field(tiles: dict, variants: list, size: int, seed: int = 3, mark: list | None = None) -> Image.Image:
    import random
    rng = random.Random(seed)
    mark = mark or DEMO_CORNERS
    rows, cols = len(mark) - 1, len(mark[0]) - 1
    img = Image.new("RGBA", (cols * size, rows * size))
    for y in range(rows):
        for x in range(cols):
            corners = [int(mark[y + dy][x + dx]) for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))]
            idx = (corners[0] << 3) | (corners[1] << 2) | (corners[2] << 1) | corners[3]
            if idx == 0 and mark is not DEMO_CORNERS:
                continue
            tile = rng.choice(variants) if idx == 0 and variants and rng.random() < 0.4 else tiles[idx]
            img.alpha_composite(tile, (x * size, y * size))
    return img


def hex_colour(text: str) -> np.ndarray:
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def recolour(tiles: dict, lower: np.ndarray, upper: np.ndarray, lower_target: np.ndarray | None, upper_target: np.ndarray | None, flatten: float = 0.0) -> dict:
    """Shift each terrain's pixels so their mean lands on the target colour, optionally flattening the upper terrain first."""
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        rgb = a[..., :3]
        is_lower = _classify(rgb, lower, upper)[..., None]
        lower_rgb = rgb + (lower_target - lower) if lower_target is not None else rgb
        upper_rgb = rgb * (1 - flatten) + upper * flatten
        if upper_target is not None:
            upper_rgb = upper_rgb + (upper_target - upper)
        a[..., :3] = np.clip(np.where(is_lower, lower_rgb, upper_rgb), 0, 255)
        out[key] = Image.fromarray(a.round().astype(np.uint8), "RGBA")
    return out


def flat_tile(colour: np.ndarray, size: int) -> Image.Image:
    return Image.new("RGBA", (size, size), tuple(int(v) for v in colour) + (255,))


def cutout(tiles: dict, lower: np.ndarray, upper: np.ndarray, white: bool = False) -> dict:
    """Keep only upper-terrain pixels (optionally as flat white) so the tile can overlay another terrain with the Wang edge."""
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        is_upper = ~_classify(a[..., :3], lower, upper)
        a[..., 3] = np.where(is_upper, 255, 0)
        if white:
            a[..., :3] = 255
        out[key] = Image.fromarray(a.round().astype(np.uint8), "RGBA")
    return out


def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def season_style(tiles: dict, lower: np.ndarray, upper: np.ndarray, style: dict) -> dict:
    """Restyle the lower terrain's elements: flower dots, lighter blades, and darker shadow patches."""
    if not style:
        return tiles
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        rgb = a[..., :3]
        is_lower = _classify(rgb, lower, upper)
        luma, base = _luma(rgb), _luma(lower[None, None, :])[0, 0]
        dots = is_lower & (rgb[..., 0] > rgb[..., 1] + 15)
        blades = is_lower & ~dots & (luma > base + 5)
        shadows = is_lower & ~dots & (luma < base - 10)
        if style.get("dots"):
            colours = [hex_colour(c) for c in style["dots"]]
            yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
            pick = ((xx // 3) * 7 + (yy // 3) * 13) % len(colours)
            palette = np.stack([np.where(pick == i, 1.0, 0.0) for i in range(len(colours))], axis=-1) @ np.stack(colours)
            rgb = np.where(dots[..., None], palette, rgb)
        if style.get("blades"):
            target = hex_colour(style["blades"])
            rgb = np.where(blades[..., None], rgb * 0.15 + target * 0.85, rgb)
        if style.get("shadow_soften"):
            amount = style["shadow_soften"]
            rgb = np.where(shadows[..., None], rgb * (1 - amount) + lower * amount, rgb)
        a[..., :3] = np.clip(rgb, 0, 255)
        out[key] = Image.fromarray(a.round().astype(np.uint8), "RGBA")
    return out


def tint(tiles: dict, factor: np.ndarray) -> dict:
    """Multiply every pixel by a colour factor (0-1 per channel); alpha is kept."""
    out = {}
    for key, im in tiles.items():
        a = np.asarray(im.convert("RGBA")).astype(float)
        a[..., :3] = np.clip(a[..., :3] * factor, 0, 255)
        out[key] = Image.fromarray(a.round().astype(np.uint8), "RGBA")
    return out


def texture_variants(tile: Image.Image, flat: np.ndarray, count: int, radius: float, seed: int = 5) -> list:
    """Distinct tiles from one seamless texture: rolled offsets and flips, each faded to flat inside an irregular round mask."""
    rng = np.random.default_rng(seed)
    a = np.asarray(tile.convert("RGBA")).astype(float)
    size = a.shape[0]
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = (size - 1) / 2
    out = []
    for i in range(count):
        rolled = np.roll(np.roll(a, int(rng.integers(0, size)), axis=0), int(rng.integers(0, size)), axis=1)
        if i % 2:
            rolled = rolled[:, ::-1]
        if i % 4 >= 2:
            rolled = rolled[::-1, :]
        angle = np.arctan2(yy - cy, xx - cx)
        wobble = 1 + 0.18 * np.sin(3 * angle + rng.uniform(0, 6.28)) + 0.12 * np.sin(5 * angle + rng.uniform(0, 6.28))
        dist = np.hypot(xx - cx, yy - cy) / (radius * wobble)
        mask = np.clip((dist - 0.55) / 0.45, 0, 1) ** 1.5
        rolled[..., :3] = rolled[..., :3] * (1 - mask[..., None]) + flat * mask[..., None]
        out.append(Image.fromarray(rolled.round().astype(np.uint8), "RGBA"))
    return out


def add_dots(tiles: list, colours: list, count: int, radius: float, seed: int = 9) -> list:
    """Sprinkle small two-pixel flower dots inside the unfaded centre of each tile."""
    if not count or not colours:
        return tiles
    rng = np.random.default_rng(seed)
    palette = [hex_colour(c) for c in colours]
    out = []
    for tile in tiles:
        a = np.asarray(tile.convert("RGBA")).astype(float)
        size = a.shape[0]
        centre = (size - 1) / 2
        for _ in range(count):
            angle, dist = rng.uniform(0, 6.28), rng.uniform(0, radius * 0.6)
            x, y = int(centre + dist * np.cos(angle)), int(centre + dist * np.sin(angle))
            colour = palette[int(rng.integers(0, len(palette)))]
            a[y, x, :3] = colour
            a[y, min(x + 1, size - 1), :3] = colour * 0.85
        out.append(Image.fromarray(a.round().astype(np.uint8), "RGBA"))
    return out
