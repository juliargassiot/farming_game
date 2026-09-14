#!/bin/bash
# Runs tests/. Arguments filter tests by substring of "file.method", e.g. tools/test.sh test_plot regrow
# A script error inside a test fails the run even when every check passed.
cd "$(dirname "$0")/.."
GODOT="$(tools/godot.sh)" || exit 1
OUT="$(timeout 300 "$GODOT" --headless --audio-driver Dummy --path . --script tools/run_tests.gd -- "$@" 2>&1)"
STATUS=$?
OUT="$(echo "$OUT" | grep -v -E '^Godot Engine|^$')"
if echo "$OUT" | grep -q -E '^(SCRIPT ERROR|USER ERROR|ERROR):'; then
	echo "$OUT"
	echo "tests failed: script errors above"
	exit 1
fi
if [ "$STATUS" -ne 0 ]; then
	echo "$OUT"
	echo "tests failed"
	exit 1
fi
echo "$OUT" | grep -E '^tests:'
