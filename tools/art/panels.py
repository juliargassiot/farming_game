#!/usr/bin/env python3
"""Large mountain panels painted by PixelLab's Pro image endpoint from the hand-drawn mockup (`mountain mockup.png`):
every mockup colour is a kind of ground, a panel's crop is tidied into flat colour blocks and handed over as the layout
reference with the river illustration as the style. `panels.py <name> x y [--seeds a,b]` paints one 600×448 panel whose
top-left sits at map pixel (x, y); results land in tools/art/raw/panels/<name>/ with a sheet in previews/art/."""
import argparse
import base64
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixellab import PixelLab, decode_image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MOCKUP = ROOT / "mountain mockup.png"
STYLE = ROOT / "river-landscape-illustration-pixel-art-style.jpg"
PANEL = (600, 448)
MAP_WIDTH = 2560
KINDS = {
    "void": ((240, 240, 240), (236, 236, 236)), "ridge": ((176, 112, 80), (110, 78, 52)), "grass": ((32, 176, 64), (96, 140, 60)),
    "path": ((0, 0, 0), (170, 130, 90)), "home": ((160, 64, 160), (150, 70, 150)), "dig": ((128, 0, 16), (150, 30, 30)),
    "cave": ((240, 160, 192), (40, 30, 30)), "lookout": ((48, 64, 192), (200, 190, 170)),
}
GUIDE_TEXT = ("layout reference for the whole panel: dark brown areas are impassable rocky ridges and stacked boulders, green areas are grassy "
              "ground with a few pine trees, the tan winding band is a worn dirt footpath, the pale area at the peak is a bare stone lookout ledge, "
              "light grey areas are bare rock ground; keep every shape where it is")


def classify(image: Image.Image) -> np.ndarray:
    """Index into KINDS per pixel by nearest mockup colour."""
    rgb = np.asarray(image.convert("RGB")).astype(int)
    keys = np.array([k[0] for k in KINDS.values()])
    dist = ((rgb[..., None, :] - keys[None, None, :, :]) ** 2).sum(axis=-1)
    return dist.argmin(axis=-1)


def guide(x: int, y: int) -> Image.Image:
    """The panel's crop of the mockup as flat colour blocks at map scale; the unpainted inside of the mountain is bare rock."""
    mock = Image.open(MOCKUP)
    scale = mock.width / MAP_WIDTH
    crop = mock.crop((int(x * scale), int(y * scale), int((x + PANEL[0]) * scale), int((y + PANEL[1]) * scale))).resize(PANEL, Image.NEAREST)
    kinds = classify(crop)
    out = np.zeros(PANEL[::-1] + (3,), dtype=np.uint8)
    for i, (_, colour) in enumerate(KINDS.values()):
        out[kinds == i] = colour
    inside = _inside_mountain(kinds)
    out[(kinds == 0) & inside] = (150, 140, 128)
    return Image.fromarray(out, "RGB")


def _inside_mountain(kinds: np.ndarray) -> np.ndarray:
    """Void pixels enclosed by anything drawn count as the mountain's unpainted interior: those with drawn pixels above them."""
    drawn = kinds != 0
    above = np.maximum.accumulate(drawn, axis=0)
    below = np.maximum.accumulate(drawn[::-1], axis=0)[::-1]
    return above & below


def _b64(image: Image.Image) -> dict:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return {"image": {"type": "base64", "base64": base64.b64encode(buffer.getvalue()).decode(), "format": "png"},
            "size": {"width": image.width, "height": image.height}}


def style_image() -> Image.Image:
    ref = Image.open(STYLE).convert("RGB")
    w, h = ref.size
    return ref.crop((int(w * 0.45), int(h * 0.15), int(w * 0.95), int(h * 0.55))).resize((1024, 819), Image.LANCZOS)


def paint(name: str, x: int, y: int, seeds: list, prompt: str) -> Path:
    folder = ROOT / "tools" / "art" / "raw" / "panels" / name
    folder.mkdir(parents=True, exist_ok=True)
    layout = guide(x, y)
    layout.save(folder / "guide.png")
    client = PixelLab()
    jobs = {}
    for seed in seeds:
        body = {"description": prompt, "image_size": {"width": PANEL[0], "height": PANEL[1]}, "seed": seed, "no_background": False,
                "reference_images": [dict(_b64(layout), usage_description=GUIDE_TEXT)],
                "style_image": _b64(style_image()), "style_options": {"color_palette": True, "outline": True, "detail": True, "shading": True}}
        jobs[seed] = client.call("POST", "/generate-image-v2", json=body)["background_job_id"]
    frames = [layout]
    for seed, job in zip(jobs, client.wait(list(jobs.values()))):
        image = _find_image(job)
        (folder / f"{seed}.png").write_bytes(decode_image(image))
        frames.append(Image.open(folder / f"{seed}.png").convert("RGB"))
    sheet = Image.new("RGB", (len(frames) * (PANEL[0] + 8), PANEL[1]), (40, 40, 48))
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * (PANEL[0] + 8), 0))
    out = ROOT / "previews" / "art" / f"panel-{name}.png"
    sheet.save(out)
    return out


def _find_image(obj) -> dict:
    if isinstance(obj, dict):
        if "base64" in obj:
            return obj
        for value in obj.values():
            found = _find_image(value)
            if found:
                return found
    if isinstance(obj, list):
        for value in obj:
            found = _find_image(value)
            if found:
                return found
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("x", type=int)
    parser.add_argument("y", type=int)
    parser.add_argument("--seeds", default="1,2")
    parser.add_argument("--prompt", default="top-down view of a rugged mountain peak for a 2D pixel art game map: a worn dirt footpath climbing between "
                        "brown stacked-stone ridges and boulders to a bare stone lookout ledge at the summit, grassy patches with a few pine trees, "
                        "weathered warm-toned rock, no sky, no horizon, the ground fills the whole frame")
    args = parser.parse_args()
    print("sheet at", paint(args.name, args.x, args.y, [int(s) for s in args.seeds.split(",")], args.prompt).relative_to(ROOT))


if __name__ == "__main__":
    main()
