"""Frame builders for crop stage animations: each returns [(RGBA image, seconds)] from one static stage image."""
import numpy as np
from PIL import Image


def _arr(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGBA")).astype(int)


def _img(a: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def _shift(a: np.ndarray, mask: np.ndarray, dx: int, dy: int, fill=None) -> np.ndarray:
    out = a.copy()
    out[mask] = fill if fill is not None else (0, 0, 0, 0)
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        ny, nx = y + dy, x + dx
        if 0 <= ny < a.shape[0] and 0 <= nx < a.shape[1]:
            out[ny, nx] = a[y, x]
    return out


def eyes(img: Image.Image) -> list:
    a = _arr(img)
    pupils = (a[..., 3] > 0) & (a[..., 0] > 180) & (a[..., 1] < 80) & (a[..., 2] < 80)
    black = (10, 10, 12, 255)
    return [(img, 2.4), (_img(_shift(a, pupils, 1, 0, black)), 0.35), (img, 1.6), (_img(_shift(a, pupils, -1, 0, black)), 0.35)]


def drip(img: Image.Image) -> list:
    a = _arr(img)
    ys = np.arange(a.shape[0])[:, None]
    xs = np.arange(a.shape[1])[None, :]
    red = (a[..., 3] > 0) & (a[..., 0] > 90) & (a[..., 1] < 70) & (a[..., 2] < 80) & (xs < 14) & (ys > 6) & (ys < 22)
    if not red.any():
        return [(img, 1.0)]
    bottom = np.nonzero(red)[0].max()
    drop = red & (ys >= bottom - 2)
    gone = _img(_shift(a, drop, 0, 40))
    return [(img, 2.6), (_img(_shift(a, drop, 0, 2)), 0.12), (_img(_shift(a, drop, 0, 5)), 0.12), (gone, 0.8),
            (_img(_shift(a, drop & (ys == bottom - 2), 0, 0)), 0.3), (img, 0.4)]


def flame(img: Image.Image) -> list:
    a = _arr(img)
    ys = np.arange(a.shape[0])[:, None]
    fire = (a[..., 3] > 0) & (a[..., 0] > 170) & (a[..., 1] > 50) & (a[..., 1] < 190) & (a[..., 2] < 90) & (ys < 20)
    if not fire.any():
        return [(img, 1.0)]
    top = np.nonzero(fire)[0].min()
    height = np.nonzero(fire)[0].max() - top + 1
    tips = fire & (ys < top + height * 0.55)
    return [(img, 0.22), (_img(_shift(a, tips, 1, 0)), 0.22), (img, 0.22), (_img(_shift(a, tips, -1, 0)), 0.22)]


def twitch(img: Image.Image) -> list:
    a = _arr(img)
    ys = np.arange(a.shape[0])[:, None]
    wings = (a[..., 3] > 0) & (a[..., 0] > 110) & (a[..., 2] > 110) & (a[..., 1] < 130) & (ys < 20)
    up = _img(_shift(a, wings, 0, -1))
    return [(img, 2.2), (up, 0.12), (img, 0.14), (up, 0.12)]


BUILDERS = {"eyes": eyes, "drip": drip, "flame": flame, "twitch": twitch}
