#!/bin/bash
# Renders a scene to previews/<name>.png (default: the scene name), optionally with the player moved to cell x,y, on another map.
set -e
cd "$(dirname "$0")/.."
GODOT="$(tools/godot.sh)"
timeout 300 "$GODOT" --headless --audio-driver Dummy --path . --import >/dev/null 2>&1
RUN=()
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
	RUN=(xvfb-run -a -s "-screen 0 1280x800x24")
fi
"${RUN[@]}" "$GODOT" --rendering-driver opengl3 --audio-driver Dummy --path . --script tools/screenshot.gd -- "$@" 2>&1 | grep -E '^(wrote|cannot|usage)' || exit 1
