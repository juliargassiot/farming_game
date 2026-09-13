#!/bin/bash
# Run before every commit. Fails when imports, type checks, tests, or comment density fail.
set -e
cd "$(dirname "$0")/.."
GODOT="$(tools/godot.sh)"
GODOT_FLAGS="--headless --audio-driver Dummy --path ."
RUN="timeout 300 $GODOT $GODOT_FLAGS"

echo "== import"
$RUN --import >/dev/null 2>&1 || $RUN --import
git add -A -- '*.import' '*.uid' 2>/dev/null || true

echo "== type check"
CHANGED="$(git diff --cached --name-only --diff-filter=AM | grep '\.gd$' || true)"
[ -z "$CHANGED" ] && CHANGED="$(git ls-files '*.gd')"
OUT="$($RUN --script tools/check_scripts.gd -- $CHANGED 2>&1)" || { echo "$OUT" | grep -E 'ERROR|at:'; echo "type check failed"; exit 1; }
echo "$OUT" | grep -E '^scripts checked'

echo "== scene load"
OUT="$($RUN --script tools/load_scenes.gd 2>&1)" || { echo "$OUT" | grep -v -E '^Godot Engine|^$'; echo "scene load failed"; exit 1; }
echo "$OUT" | grep -E '^scenes loaded'

echo "== tests"
OUT="$($RUN --script tools/run_tests.gd 2>&1)" || { echo "$OUT" | grep -v -E '^Godot Engine|^$'; echo "tests failed"; exit 1; }
echo "$OUT" | grep -E '^tests:'

echo "== deck installer"
python3 deck/steam_shortcuts.py --self-test
bash -n deck/install.sh deck/setup.sh deck/play.sh

echo "== comment density"
STAGED="$(git diff --cached --name-only --diff-filter=AM || true)"
[ -z "$STAGED" ] && STAGED="$(git ls-files)"
echo "$STAGED" | python3 tools/comment_density.py --stdin
echo "preflight ok"
