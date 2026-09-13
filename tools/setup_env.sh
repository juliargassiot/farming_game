#!/bin/bash
# Prepares a fresh checkout: Python deps, git hooks, pinned Godot. Safe to re-run.
cd "$(dirname "$0")/.."
python3 -m pip install --quiet --disable-pip-version-check -r tools/requirements.txt 2>&1 | grep -v -i 'warning' || true
git config core.hooksPath .githooks
tools/godot.sh >/dev/null || echo "Godot download failed; preflight will retry" >&2
