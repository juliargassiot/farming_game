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
