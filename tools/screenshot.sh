#!/bin/bash
# Renders a scene to previews/<scene>.png. Uses a virtual display when none is available.
set -e
cd "$(dirname "$0")/.."
GODOT="$(tools/godot.sh)"
timeout 300 "$GODOT" --headless --audio-driver Dummy --path . --import >/dev/null 2>&1
RUN=()
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
	RUN=(xvfb-run -a -s "-screen 0 1280x800x24")
fi
"${RUN[@]}" "$GODOT" --rendering-driver opengl3 --audio-driver Dummy --path . --script tools/screenshot.gd -- "$1" 2>&1 | grep -E '^(wrote|cannot|usage)' || exit 1
