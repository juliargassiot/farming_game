#!/bin/bash
# One-shot Steam Deck or Linux laptop install. From a terminal in Desktop Mode:
#   curl -fsSL https://raw.githubusercontent.com/juliargassiot/farming_game/main/deck/install.sh | bash
# Installs git if missing, clones or updates the game, installs Godot, and registers the Steam shortcuts.
set -e
REPO="${FARM_REPO:-https://github.com/juliargassiot/farming_game.git}"
FARM="$HOME/games/farm"
STEAM="${STEAM_DIR:-$HOME/.steam/steam}"
BREW=/home/linuxbrew/.linuxbrew/bin
[ -d "$BREW" ] && export PATH="$BREW:$PATH"

if ! command -v git >/dev/null; then
	echo "== installing git"
	if ! [ -x "$BREW/brew" ]; then
		NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
		grep -q linuxbrew ~/.bashrc 2>/dev/null || echo 'eval "$('"$BREW"'/brew shellenv)"' >> ~/.bashrc
		export PATH="$BREW:$PATH"
	fi
	brew install git </dev/null
fi

echo "== game"
if [ -d "$FARM/.git" ]; then
	git -C "$FARM" fetch --quiet origin main
	git -C "$FARM" checkout --quiet --force main 2>/dev/null || git -C "$FARM" checkout --quiet --force -b main origin/main
	git -C "$FARM" reset --quiet --hard origin/main
else
	mkdir -p "$(dirname "$FARM")"
	git clone --quiet "$REPO" "$FARM" </dev/null
fi

echo "== godot"
"$FARM/deck/setup.sh"

echo "== steam shortcuts"
restart_steam=0
if pgrep -x steam >/dev/null 2>&1; then
	echo "Closing Steam so the shortcuts can be saved"
	steam -shutdown >/dev/null 2>&1 || true
	for _ in $(seq 60); do pgrep -x steam >/dev/null || break; sleep 1; done
	pgrep -x steam >/dev/null && { echo "Steam did not close; quit it and rerun this script"; exit 1; }
	restart_steam=1
fi
python3 "$FARM/deck/steam_shortcuts.py" "$FARM" "$STEAM"
[ "$restart_steam" = 1 ] && command -v steam >/dev/null && (nohup steam >/dev/null 2>&1 &)

echo
echo "Done. Farm and Farm (stable) are in the Steam library; return to Game Mode to play."
