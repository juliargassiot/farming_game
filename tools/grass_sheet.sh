#!/bin/bash
# Renders every grass preset on the test strip and stacks them, labelled, into previews/grass-sheet.png.
set -e
cd "$(dirname "$0")/.."
GODOT="$(tools/godot.sh)"
timeout 300 "$GODOT" --headless --audio-driver Dummy --path . --import >/dev/null 2>&1
RUN=()
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
	RUN=(xvfb-run -a -s "-screen 0 1280x800x24")
fi
"${RUN[@]}" "$GODOT" --rendering-driver opengl3 --audio-driver Dummy --path . --script tools/grass_sheet.gd 2>&1 | grep -E '^wrote' || exit 1
python3 - <<'PY'
import json
from PIL import Image, ImageDraw
presets = list(json.load(open("data/grass.json"))["presets"])
panels = [Image.open(f"previews/grass/{p}.png").convert("RGBA") for p in presets]
sheet = Image.new("RGBA", (panels[0].width, sum(p.height + 28 for p in panels)), (30, 30, 36, 255))
y = 0
for name, panel in zip(presets, panels):
    ImageDraw.Draw(sheet).text((8, y + 6), name, fill=(255, 255, 255, 255))
    sheet.alpha_composite(panel, (0, y + 28))
    y += panel.height + 28
sheet.save("previews/grass-sheet.png")
print("wrote previews/grass-sheet.png")
PY
