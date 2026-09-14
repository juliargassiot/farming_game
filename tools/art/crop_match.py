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
    soil = alpha & ~leaf & low & (luma < 110) & (r >= g) & (r < 170) & (r - b < 80)
    marks = alpha & ((luma < 40) | ((r > 150) & (g < 80) & (b < 80)))
    body = alpha & ~leaf & ~soil & ~marks
    return {"soil": soil, "leaf": leaf, "body": body}


def match(target: Image.Image, reference: Image.Image, classes: dict, soil_from_row: int = 20, reference_soil_from_row: int = 12) -> Image.Image:
    """classes: {name: "palette" | "tint" | "shift" | "luma"}. palette takes the reference's own colours by brightness rank; tint keeps the
    target's shading but recolours it to the reference hue; shift moves the class mean onto the reference's; luma only scales brightness."""
    t = np.asarray(target.convert("RGBA")).astype(float)
    r = np.asarray(reference.convert("RGBA")).astype(float)
    tc, rc = _classes(t, soil_from_row), _classes(r, reference_soil_from_row)
    for name, mode in classes.items():
        if not (tc[name].any() and rc[name].any()):
            continue
        mean_t, mean_r = t[tc[name]][:, :3].mean(axis=0), r[rc[name]][:, :3].mean(axis=0)
        if mode == "palette":
            src, ref = t[tc[name]][:, :3], r[rc[name]][:, :3]
            ref_sorted = ref[np.argsort(ref.mean(axis=1))]
            ranks = np.argsort(np.argsort(src.mean(axis=1))) / max(1, len(src) - 1)
            t[tc[name], :3] = ref_sorted[(ranks * (len(ref_sorted) - 1)).round().astype(int)]
        elif mode == "tint":
            weights = np.array([0.299, 0.587, 0.114])
            ref = r[rc[name]][:, :3]
            light = ref[(ref @ weights) >= np.median(ref @ weights)].mean(axis=0)
            luma = t[tc[name], :3] @ weights
            luma = luma * ((ref @ weights).mean() / max(1.0, luma.mean()))
            t[tc[name], :3] = np.clip(light[None, :] * (luma / max(1.0, light @ weights))[:, None], 0, 255)
        elif mode == "shift":
            t[tc[name], :3] = np.clip(t[tc[name], :3] + (mean_r - mean_t), 0, 255)
        else:
            t[tc[name], :3] = np.clip(t[tc[name], :3] * (mean_r.mean() / max(1.0, mean_t.mean())), 0, 255)
    return Image.fromarray(t.round().astype(np.uint8), "RGBA")
