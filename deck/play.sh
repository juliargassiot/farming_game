#!/bin/bash
# Steam Deck launcher: update the chosen branch, then run the game until it quits.
# Exit code 42 from the game means "check for updates": pull again and relaunch.
FARM="$HOME/games/farm"
GODOT="$HOME/games/godot"
BRANCH="${1:-main}"
[ -d /home/linuxbrew/.linuxbrew/bin ] && export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"
cd "$FARM" || { zenity --error --text "Farm is not installed at $FARM" 2>/dev/null; exit 1; }

update() {
	git fetch --quiet origin "$BRANCH" || return 0
	git checkout --quiet --force "$BRANCH" 2>/dev/null || git checkout --quiet --force -b "$BRANCH" "origin/$BRANCH" || return 0
	git reset --quiet --hard "origin/$BRANCH"
}

update
while true; do
	"$GODOT" --path . --fullscreen
	code=$?
	if [ "$code" -eq 42 ]; then
		update
		continue
	fi
	exit "$code"
done
