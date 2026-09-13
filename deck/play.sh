#!/bin/bash
# Steam Deck launcher: update the chosen branch, import its assets, then run the game until it quits.
# Exit code 42 from the game means "check for updates": pull again and relaunch.
# When the pull changes this script, it re-executes itself so the new version runs at once.
FARM="$HOME/games/farm"
GODOT="$HOME/games/godot"
BRANCH="${1:-main}"
[ -d /home/linuxbrew/.linuxbrew/bin ] && export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"
cd "$FARM" || { zenity --error --text "Farm is not installed at $FARM" 2>/dev/null; exit 1; }

update() {
	git fetch --quiet origin "$BRANCH" || return 0
	git checkout --quiet --force "$BRANCH" 2>/dev/null || git checkout --quiet --force -b "$BRANCH" "origin/$BRANCH" || return 0
	git reset --quiet --hard "origin/$BRANCH"
	"$GODOT" --headless --path . --import >/dev/null 2>&1 || true
}

before="$(md5sum "$0")"
update
if [ -z "$FARM_RELAUNCHED" ] && [ "$(md5sum "$0")" != "$before" ]; then
	FARM_RELAUNCHED=1 exec "$0" "$@"
fi
command -v python3 >/dev/null && python3 deck/steam_shortcuts.py --art "$FARM" >/dev/null 2>&1
while true; do
	"$GODOT" --path . --fullscreen
	code=$?
	if [ "$code" -eq 42 ]; then
		update
		continue
	fi
	exit "$code"
done
