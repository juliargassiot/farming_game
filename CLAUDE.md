# Farm

Cozy farming/romance game for the Steam Deck. Godot 4.7.2 (pinned in `tools/godot.sh`; the Deck runs the same binary from source, no build step). GDScript only, with static typing everywhere: untyped or inferred declarations are errors (see `[debug]` in `project.godot`). Use typed arrays, typed dictionaries, and enums for game data.

The user does not understand or read code, documentation, commits, or comments. The user chooses; Claude generates, proposes, and wires. Walkthroughs written for the user (setup steps, one-time instructions) are temporary: when the user reports finishing them, delete them in that same change without being asked. The scripts they pointed at stay. Every push lands on `main`: commit, merge the working branch into `main` (fast-forward when possible), and push `main`, resolving any problem (conflicts, failed checks) yourself. "Let's push" means exactly that. "Promote to stable" means fast-forward `stable` to `main` and push.

## Before every commit

- Run `tools/preflight.sh` and never push if it fails. It imports assets, type-checks changed scripts, runs `tests/`, and checks comment density.
- After any visual change, run `tools/screenshot.sh scenes/<system>/<scene>.tscn`, open the PNG it writes under `previews/`, and confirm the result before committing. Committed previews are how the user reviews visuals.

## Layout

- `scenes/<system>/` and `scripts/<system>/` mirror each other; one system per folder, scenes small and single-purpose. Check `scenes/` and `data/` before inventing anything.
- `data/` holds crops, maps, dialogue, and schedules as JSON or text.
- `assets/` holds PNGs and Godot resources. Save data goes to `user://`; never write to the repo at runtime.
- Screen is 640×400, integer-scaled ×2 to the Deck's 1280×800. Tiles are 16 px; character frames are 32×32.

## Art

Follow `tools/art/README.md`. Never run rotate, animate, or import for a design that `tools/art/generated.json` does not mark approved. Never change approved art without being asked. Hand-authored pixel art is a string grid under `tools/art/grids/`, converted by `tools/art/art.py placeholders`; the PNG is what Godot uses.

## Comments and documentation

When writing documentation or comments, prefer replacing incorrect information with correct information, rather than explicitly correcting the incorrect information and leaving references to the incorrect information. We do not maintain a record of what the code doesn't do. When writing comments, do not write the entire provenance of the change - even the 'why' behind the change is irrelevant if it's obvious from the code.

Comment lines, excepting trailing comments, must not exceed 20% of the file or 10 lines, whichever is largest. `tools/comment_density.py` enforces this in hooks and in preflight. Claude MUST address violations by tightening or removing prose, not padding code. If Claude is deleting code, then Claude may additionally need to tighten or remove prose.

We keep documentation directory-scoped or in skills. The three biggest failure modes are maintaining a graveyard of past decisions or corrections that won't again be relevant, overly verbose prose, and duplicating documentation in multiple locations to keep it synced — pointers are preferred, but even duplication of pointers can become problematic.
