#!/bin/bash
# Prints the path to the pinned Godot binary, downloading it into ~/.cache when absent.
VERSION="4.7.2"
NAME="Godot_v${VERSION}-stable_linux.x86_64"
CACHE="${GODOT_CACHE:-$HOME/.cache/godot}"

usable() { [ -n "$1" ] && [ -x "$1" ] && "$1" --version 2>/dev/null | grep -q "^${VERSION}\."; }

for candidate in "$GODOT" "$HOME/games/godot" "$CACHE/$NAME" "$(command -v godot)"; do
	if usable "$candidate"; then
		echo "$candidate"
		exit 0
	fi
done

mkdir -p "$CACHE"
URL="https://downloads.godotengine.org/?version=${VERSION}&flavor=stable&slug=linux.x86_64.zip"
echo "Downloading Godot ${VERSION} to $CACHE" >&2
curl -fsSL --retry 3 -o "$CACHE/godot.zip" "$URL" && unzip -o -q "$CACHE/godot.zip" -d "$CACHE" && chmod +x "$CACHE/$NAME"
rm -f "$CACHE/godot.zip"
if usable "$CACHE/$NAME"; then
	echo "$CACHE/$NAME"
	exit 0
fi
echo "Godot ${VERSION} could not be installed" >&2
exit 1
