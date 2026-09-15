#!/usr/bin/env python3
"""Large mountain panels painted by PixelLab's Pro image endpoint from the hand-drawn mockup (`mountain mockup.png`):
every mockup colour is a kind of ground, a panel's crop is tidied into flat colour blocks and handed over as the layout
reference with the river illustration as the style. `panels.py one <name> x y [--seeds a,b]` paints one 600×448 panel
whose top-left sits at map pixel (x, y); `panels.py map [--seed n]` paints every panel of the map grid, each also shown
the finished panel above it, and `panels.py stitch` blends them into tools/art/raw/panels/fangridge.png."""
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
ART_SCALE = 2
ART_WIDTH, ART_HEIGHT = 1920, 1440
DETAIL, DETAIL_OVERLAP, DETAIL_STRENGTH = 200, 24, 450
MAP_WIDTH, MAP_HEIGHT = ART_WIDTH * ART_SCALE, ART_HEIGHT * ART_SCALE
OVERLAP = (48, 32)
KINDS = {
    "void": ((240, 240, 240), (236, 236, 236)), "ridge": ((176, 112, 80), (110, 78, 52)), "grass": ((32, 176, 64), (96, 140, 60)),
    "path": ((0, 0, 0), (170, 130, 90)), "home": ((160, 64, 160), (150, 70, 150)), "dig": ((128, 0, 16), (150, 30, 30)),
    "cave": ((240, 160, 192), (40, 30, 30)), "lookout": ((48, 64, 192), (200, 190, 170)),
}
GUIDE_TEXT = ("layout, keep every shape where it is: dark brown = impassable rocky ridges and boulders, green = grass with a few pines, "
              "tan band = dirt footpath, light grey = bare rock ground, pale summit patch = natural flat rock lookout, purple = flat cleared "
              "ground for a cabin, dark red = roped-off dig pit of bare earth, black arch = cave mouth, light grey-white beyond the "
              "mountain = open sky, clouds and distant hazy mountains")
NEIGHBOUR_TEXT = "the finished painting of the panel directly above this one: continue its rock, grass and path seamlessly along the top edge"
OVERVIEW_TEXT = ("this exact region of the finished map painting at low resolution: repaint it faithfully, same shapes, colours and style, "
                 "with fine pixel detail")
OVERVIEW = ROOT / "tools" / "art" / "raw" / "panels" / "overview" / "chosen.png"
PROMPT = ("top-down view of part of a rugged mountain for a 2D pixel art game map: worn dirt footpaths winding between brown stacked-stone "
          "ridges and boulders, grassy patches with a few pine trees, bare weathered warm-toned rock ground, and beyond the mountain's edge "
          "open sky with soft clouds and distant hazy mountains, the ground fills the frame")


def classify(image: Image.Image) -> np.ndarray:
    """Index into KINDS per pixel by nearest mockup colour."""
    rgb = np.asarray(image.convert("RGB")).astype(int)
    keys = np.array([k[0] for k in KINDS.values()])
    dist = ((rgb[..., None, :] - keys[None, None, :, :]) ** 2).sum(axis=-1)
    return dist.argmin(axis=-1)


def guide(x: int, y: int) -> Image.Image:
    """The panel's crop of the mockup as flat colour blocks at art scale; the unpainted inside of the mountain is bare rock."""
    mock = Image.open(MOCKUP)
    scale = mock.width / ART_WIDTH
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


def overview_crop(x: int, y: int) -> Image.Image:
    """The chosen whole-map painting's crop for a panel, brought up to panel size."""
    whole = Image.open(OVERVIEW).convert("RGB").resize((MAP_WIDTH, MAP_HEIGHT), Image.LANCZOS)
    return whole.crop((x, y, x + PANEL[0], y + PANEL[1]))


def request(client: PixelLab, layout: Image.Image, seed: int, prompt: str, above: Image.Image | None = None, x: int | None = None, y: int | None = None) -> str:
    references = []
    if x is not None and OVERVIEW.exists():
        references.append(dict(_b64(overview_crop(x, y)), usage_description=OVERVIEW_TEXT))
    references.append(dict(_b64(layout), usage_description=GUIDE_TEXT))
    if above is not None:
        references.append(dict(_b64(above), usage_description=NEIGHBOUR_TEXT))
    body = {"description": prompt, "image_size": {"width": PANEL[0], "height": PANEL[1]}, "seed": seed, "no_background": False,
            "reference_images": references, "style_image": _b64(style_image()),
            "style_options": {"color_palette": True, "outline": True, "detail": True, "shading": True}}
    return client.call("POST", "/generate-image-v2", json=body)["background_job_id"]


def grid() -> list:
    """Panel origins covering the art canvas with OVERLAP between neighbours, as (column, row, x, y)."""
    cols = -(-(ART_WIDTH - OVERLAP[0]) // (PANEL[0] - OVERLAP[0]))
    rows = -(-(ART_HEIGHT - OVERLAP[1]) // (PANEL[1] - OVERLAP[1]))
    out = []
    for row in range(rows):
        for col in range(cols):
            x = min(col * (PANEL[0] - OVERLAP[0]), ART_WIDTH - PANEL[0])
            y = min(row * (PANEL[1] - OVERLAP[1]), ART_HEIGHT - PANEL[1])
            out.append((col, row, x, y))
    return out


def paint_map(seed: int) -> None:
    """Every panel of the grid, a row at a time so each can see the finished panel above it; panels already painted are kept."""
    folder = ROOT / "tools" / "art" / "raw" / "panels" / "map"
    folder.mkdir(parents=True, exist_ok=True)
    client = PixelLab()
    rows = sorted({row for _, row, _, _ in grid()})
    for row in rows:
        jobs = {}
        for col, r, x, y in grid():
            if r != row or (folder / f"{col}_{row}.png").exists():
                continue
            layout = guide(x, y)
            layout.save(folder / f"{col}_{row}_guide.png")
            above = folder / f"{col}_{row - 1}.png"
            jobs[(col, row)] = request(client, layout, seed, PROMPT, Image.open(above).convert("RGB") if above.exists() else None, x, y)
        for key, job in zip(jobs, client.wait(list(jobs.values()))):
            (folder / f"{key[0]}_{key[1]}.png").write_bytes(decode_image(_find_image(job)))
            print("painted", key)


def stitch() -> Path:
    """Blends the painted grid into one image, feathering every overlap, then scales it up to map size with EPX so the
    pixels stay crisp."""
    folder = ROOT / "tools" / "art" / "raw" / "panels" / "map"
    canvas = np.zeros((ART_HEIGHT, ART_WIDTH, 3))
    weight = np.zeros((ART_HEIGHT, ART_WIDTH))
    ramp_x = np.minimum(np.minimum(np.arange(PANEL[0]) + 1, PANEL[0] - np.arange(PANEL[0])), OVERLAP[0]) / OVERLAP[0]
    ramp_y = np.minimum(np.minimum(np.arange(PANEL[1]) + 1, PANEL[1] - np.arange(PANEL[1])), OVERLAP[1]) / OVERLAP[1]
    feather = ramp_y[:, None] * ramp_x[None, :]
    for col, row, x, y in grid():
        panel = np.asarray(Image.open(folder / f"{col}_{row}.png").convert("RGB")).astype(float)
        canvas[y:y + PANEL[1], x:x + PANEL[0]] += panel * feather[..., None]
        weight[y:y + PANEL[1], x:x + PANEL[0]] += feather
    art = (canvas / np.maximum(weight, 1e-6)[..., None]).round().astype(np.uint8)
    out = ROOT / "tools" / "art" / "raw" / "panels" / "fangridge.png"
    Image.fromarray(epx(art), "RGB").save(out)
    return out


def detail_pass(seed: int) -> Path:
    """The chosen overview doubled with EPX and repainted tile by tile from itself by the older endpoint, which keeps
    every shape and adds texture; enlarged to map size and repainted once more, so the map is drawn at its own resolution."""
    raw = ROOT / "tools" / "art" / "raw" / "panels"
    base = epx(np.asarray(Image.open(OVERVIEW).convert("RGB")))
    first = _detail(base, raw / "detail", seed)
    full = np.asarray(Image.fromarray(first).resize((MAP_WIDTH, MAP_HEIGHT), Image.LANCZOS))
    final = _detail(full, raw / "detail-full", seed)
    out = raw / "fangridge.png"
    Image.fromarray(final, "RGB").save(out)
    return out


def _detail(source: np.ndarray, folder: Path, seed: int) -> np.ndarray:
    """Repaints an image tile by tile from itself, feathering the overlaps together; finished tiles are kept."""
    folder.mkdir(parents=True, exist_ok=True)
    art = Image.fromarray(source)
    height, width = source.shape[:2]
    style = style_image().crop((100, 100, 700, 700)).resize((DETAIL, DETAIL), Image.LANCZOS)
    client = PixelLab()
    step = DETAIL - DETAIL_OVERLAP
    origins = [(min(x, width - DETAIL), min(y, height - DETAIL)) for y in range(0, height - DETAIL_OVERLAP, step) for x in range(0, width - DETAIL_OVERLAP, step)]
    canvas = np.zeros((height, width, 3))
    weight = np.zeros((height, width))
    ramp = np.minimum(np.minimum(np.arange(DETAIL) + 1, DETAIL - np.arange(DETAIL)), DETAIL_OVERLAP) / DETAIL_OVERLAP
    feather = ramp[:, None] * ramp[None, :]
    for x, y in dict.fromkeys(origins):
        path = folder / f"{x}_{y}.png"
        if not path.exists():
            crop = art.crop((x, y, x + DETAIL, y + DETAIL))
            body = {"description": PROMPT, "image_size": {"width": DETAIL, "height": DETAIL}, "init_image": _b64(crop)["image"],
                    "init_image_strength": DETAIL_STRENGTH, "style_image": _b64(style)["image"], "style_strength": 40, "text_guidance_scale": 7,
                    "no_background": False, "seed": seed, "outline": "single color black outline", "shading": "detailed shading",
                    "detail": "highly detailed", "view": "high top-down"}
            response = client.call("POST", "/create-image-bitforge", json=body)
            path.write_bytes(decode_image(response.get("image") or _find_image(response)))
            print("detailed", folder.name, x, y, flush=True)
        tile = np.asarray(Image.open(path).convert("RGB")).astype(float)
        canvas[y:y + DETAIL, x:x + DETAIL] += tile * feather[..., None]
        weight[y:y + DETAIL, x:x + DETAIL] += feather
    return (canvas / np.maximum(weight, 1e-6)[..., None]).round().astype(np.uint8)


def epx(img: np.ndarray) -> np.ndarray:
    """Doubles a pixel image the EPX way: each pixel becomes four, and where two neighbouring sides agree the corner
    between them takes their colour, so diagonals stay sharp instead of stair-stepping."""
    up = np.pad(img, ((1, 0), (0, 0), (0, 0)), mode="edge")[:-1]
    down = np.pad(img, ((0, 1), (0, 0), (0, 0)), mode="edge")[1:]
    left = np.pad(img, ((0, 0), (1, 0), (0, 0)), mode="edge")[:, :-1]
    right = np.pad(img, ((0, 0), (0, 1), (0, 0)), mode="edge")[:, 1:]
    same = lambda a, b: (a == b).all(axis=-1)
    ud, lr = same(up, down), same(left, right)
    ok = ~ud & ~lr
    out = np.repeat(np.repeat(img, 2, axis=0), 2, axis=1)
    for dy, dx, a, b in ((0, 0, up, left), (0, 1, up, right), (1, 0, down, left), (1, 1, down, right)):
        pick = ok & same(a, b)
        out[dy::2, dx::2][pick] = a[pick]
    return out


def paint(name: str, x: int, y: int, seeds: list, prompt: str) -> Path:
    folder = ROOT / "tools" / "art" / "raw" / "panels" / name
    folder.mkdir(parents=True, exist_ok=True)
    layout = guide(x, y)
    layout.save(folder / "guide.png")
    client = PixelLab()
    jobs = {seed: request(client, layout, seed, prompt, None, x, y) for seed in seeds}
    frames = [overview_crop(x, y), layout] if OVERVIEW.exists() else [layout]
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
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("one")
    one.add_argument("name")
    one.add_argument("x", type=int)
    one.add_argument("y", type=int)
    one.add_argument("--seeds", default="1,2")
    one.add_argument("--prompt", default=PROMPT)
    whole = sub.add_parser("map")
    whole.add_argument("--seed", type=int, default=22)
    sub.add_parser("stitch")
    fine = sub.add_parser("detail")
    fine.add_argument("--seed", type=int, default=22)
    args = parser.parse_args()
    if args.command == "one":
        print("sheet at", paint(args.name, args.x, args.y, [int(s) for s in args.seeds.split(",")], args.prompt).relative_to(ROOT))
    elif args.command == "map":
        paint_map(args.seed)
    elif args.command == "detail":
        print("wrote", detail_pass(args.seed).relative_to(ROOT))
    else:
        print("wrote", stitch().relative_to(ROOT))


if __name__ == "__main__":
    main()
