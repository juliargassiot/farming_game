"""Contact sheets: frames laid out in labelled rows, scaled up so they read on a phone."""
from PIL import Image, ImageDraw

LABEL_W = 56
PAD = 2


def contact_sheet(rows: list[tuple[str, list[Image.Image]]], scale: int = 2) -> Image.Image:
    cell_w = max((f.width for _, frames in rows for f in frames), default=16)
    cell_h = max((f.height for _, frames in rows for f in frames), default=16)
    columns = max((len(frames) for _, frames in rows), default=1)
    width = LABEL_W + columns * (cell_w * scale + PAD)
    height = len(rows) * (cell_h * scale + 12 + PAD)
    sheet = Image.new("RGBA", (width, height), (40, 40, 48, 255))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for label, frames in rows:
        draw.text((2, y + 2), label, fill=(230, 230, 230, 255))
        for i, frame in enumerate(frames):
            x = LABEL_W + i * (cell_w * scale + PAD)
            draw.text((x, y), str(i), fill=(255, 220, 120, 255))
            box = Image.new("RGBA", (cell_w * scale, cell_h * scale), (90, 90, 100, 255) if i % 2 else (70, 70, 80, 255))
            big = frame.resize((frame.width * scale, frame.height * scale), Image.NEAREST)
            box.alpha_composite(big, ((cell_w - frame.width) * scale // 2, (cell_h - frame.height) * scale // 2))
            sheet.alpha_composite(box, (x, y + 12))
        y += cell_h * scale + 12 + PAD
    return sheet


def upscaled(image: Image.Image, scale: int = 6) -> Image.Image:
    return image.resize((image.width * scale, image.height * scale), Image.NEAREST)


def face_strip(frames: list[Image.Image], box: tuple[int, int, int, int], scale: int = 8) -> Image.Image:
    w, h = box[2] - box[0], box[3] - box[1]
    strip = Image.new("RGBA", (len(frames) * (w * scale + PAD) + PAD, h * scale + 2 * PAD), (60, 70, 50, 255))
    for i, frame in enumerate(frames):
        strip.alpha_composite(frame.crop(box).resize((w * scale, h * scale), Image.NEAREST), (PAD + i * (w * scale + PAD), PAD))
    return strip


def labelled_grid(items: list, columns: int = 5, scale: int = 4) -> Image.Image:
    """Named tiles in rows of `columns`, each scaled up with its label underneath."""
    cell_w = max(im.width for _, im in items) * scale + 2 * PAD
    cell_h = max(im.height for _, im in items) * scale + 14 + 2 * PAD
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), (40, 40, 48, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(items):
        x, y = (i % columns) * cell_w + PAD, (i // columns) * cell_h + PAD
        sheet.alpha_composite(im.resize((im.width * scale, im.height * scale), Image.NEAREST), (x, y))
        draw.text((x, y + im.height * scale + 2), label, fill=(230, 230, 230, 255))
    return sheet

