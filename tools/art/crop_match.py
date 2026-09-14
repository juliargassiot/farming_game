"""Match the colours of one crop stage to another: each colour class (soil, leaf, body) is shifted so its mean lands on the reference's."""
import numpy as np
from PIL import Image


def _classes(a: np.ndarray, soil_from_row: int = 20) -> dict:
    """Soil is the dark brown of the mound, which only lives in the lower rows; dark shading higher up belongs to the plant."""
    rgb, alpha = a[..., :3], a[..., 3] > 0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    low = np.arange(a.shape[0])[:, None] >= soil_from_row
    leaf = alpha & (g > r + 12) & (g > b + 12)
    soil = alpha & ~leaf & low & (luma < 110) & (r >= g) & (r < 170)
    body = alpha & ~leaf & ~soil
    return {"soil": soil, "leaf": leaf, "body": body}


def match(target: Image.Image, reference: Image.Image, classes: dict) -> Image.Image:
    """classes: {name: "shift" | "luma"}. shift moves the class mean onto the reference's; luma only scales brightness to match."""
    t = np.asarray(target.convert("RGBA")).astype(float)
    r = np.asarray(reference.convert("RGBA")).astype(float)
    tc, rc = _classes(t), _classes(r)
    for name, mode in classes.items():
        if not (tc[name].any() and rc[name].any()):
            continue
        mean_t, mean_r = t[tc[name]][:, :3].mean(axis=0), r[rc[name]][:, :3].mean(axis=0)
        if mode == "shift":
            t[tc[name], :3] = np.clip(t[tc[name], :3] + (mean_r - mean_t), 0, 255)
        else:
            t[tc[name], :3] = np.clip(t[tc[name], :3] * (mean_r.mean() / max(1.0, mean_t.mean())), 0, 255)
    return Image.fromarray(t.round().astype(np.uint8), "RGBA")
