#!/bin/bash
# Run once on the Deck after cloning: installs the pinned Godot next to the game and does the first import.
set -e
[ -d /home/linuxbrew/.linuxbrew/bin ] && export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"
FARM="$(cd "$(dirname "$0")/.." && pwd)"
GODOT="$HOME/games/godot"
VERSION="4.7.2"
if ! [ -x "$GODOT" ] || ! "$GODOT" --version 2>/dev/null | grep -q "^${VERSION}\."; then
	echo "Downloading Godot $VERSION"
	curl -fL --retry 3 -o /tmp/godot.zip "https://downloads.godotengine.org/?version=${VERSION}&flavor=stable&slug=linux.x86_64.zip"
	rm -rf /tmp/godot-unzip && unzip -q /tmp/godot.zip -d /tmp/godot-unzip
	mkdir -p "$(dirname "$GODOT")"
	mv "/tmp/godot-unzip/Godot_v${VERSION}-stable_linux.x86_64" "$GODOT"
	chmod +x "$GODOT"
	rm -rf /tmp/godot.zip /tmp/godot-unzip
fi
echo "Godot $("$GODOT" --version)"
chmod +x "$FARM/deck/play.sh"
cd "$FARM" && "$GODOT" --headless --path . --import >/dev/null 2>&1 || true
echo "Ready. Launch with: $FARM/deck/play.sh"
