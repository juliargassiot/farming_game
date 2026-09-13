# Art pipeline

Two sources, one destination: hand-made or purchased PNGs go straight into `assets/`; generated art comes from PixelLab through `tools/art/art.py`, which wraps the v2 HTTP API so every step is deterministic and re-runnable. Records live in `generated.json` (ids, seeds, usage, kept frames, approval). Raw downloads live in `raw/` and are committed so later steps never depend on PixelLab keeping them.

Token: set `PIXELLAB_TOKEN` in the environment or write it to `tools/art/token` (ignored by git). `art.py balance` shows remaining credits.

## Characters

Declare the character in `bodies.json` (prompt, canvas size as one number or `[width, height]`, directions, animations with an `action` text or a PixelLab `template` id, frame count, fps), then:

1. `art.py design <name>` — one Pixen generation of the south-facing sprite. Writes `previews/art/<name>-design.png`. Commit and stop. Candidate sweeps and pixel edits happen in scratch scripts; `design <name> --source <png>` adopts the winner without a generation.
2. Approval — the user looks at the preview and says yes or asks for changes. Record a yes with `art.py approve <name>` (a no with `--reject --note "..."`). Nothing below runs without it; a regenerated design clears approval.
3. `art.py rotate <name>` — turns the approved design into a stored PixelLab character with 8 rotations and downloads the declared directions. Preview: `<name>-rotations.png`.
4. `art.py animate <name> [animation] [--direction d]` — one job per direction per animation; `--direction` redoes one direction and keeps the rest. Preview: `<name>-<animation>.png`, frames numbered.
5. Judge and trim — inspect each sheet; record the frames to keep with `art.py trim <name> <animation> <direction|all> <from> <to>`. Tail frames are the usual failure.
6. `art.py import <name>` — writes `assets/characters/<name>/<animation>.png` (rows are directions) and `assets/characters/<name>/<name>.tres`, a SpriteFrames whose animations are named `<animation>_<direction>` plus `stand_<direction>` from the rotations.
7. Wire — an `AnimatedSprite2D` in the character's scene plays animations by name.

Costs (confirm with `balance`): design 1 generation, rotate 1, animations vary per direction. Sizes are set per body in `bodies.json`.

## Tiles

Declare the pair of terrains in `tiles.json`, then `art.py tile-design <name>` (one Wang tileset job, preview `<name>-design.png`), approval as above, and `art.py tile-import <name>` which writes `assets/tiles/<name>.png` (4×4 atlas ordered by corner mask NW NE SW SE, upper terrain = 1) and a `.tres` TileSet with a Match Corners terrain set so maps can be painted in the editor.

## Placeholders

Small hand-authored pixel art is a string grid under `grids/`: `@out` names the PNG, `@at col row` places the grid inside it, `@scale n` upscales, `@<char> #rrggbb|none` defines the palette, and every other line is a row of pixels. `art.py placeholders` converts every grid and writes the resources listed in `placeholders.json`.
