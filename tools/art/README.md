# Art pipeline

Two sources, one destination: hand-made or purchased PNGs go straight into `assets/`; generated art comes from PixelLab through `tools/art/art.py`, which wraps the v2 HTTP API so every step is deterministic and re-runnable. Records live in `generated.json` (ids, seeds, usage, kept frames, approval). Raw downloads live in `raw/` and are committed so later steps never depend on PixelLab keeping them.

Token: set `PIXELLAB_TOKEN` in the environment or write it to `tools/art/token` (ignored by git). `art.py balance` shows remaining credits.

The account is shared with another game. Every stored character is named `farming-game/<name>` and tagged `farming-game` plus its own name (`art.py tag` re-applies this); the API offers no project or tag field on image, edit, or tileset jobs, so their prompts are the only marker.

## Characters

Declare the character in `bodies.json` (prompt, canvas size as one number or `[width, height]`, directions, animations with an `action` text or a PixelLab `template` id, frame count, fps), then:

1. `art.py candidates <name> [--seeds a,b] [--views ...] [--prompts file] [--face x0,y0,x1,y1]` — a numbered sheet the user picks from; the seed and view of a pick are what keep its face and pose through later prompt changes. `art.py edit <name> <png> "<instruction>"` changes one thing on one image. `art.py design <name> --source <png>` adopts the winner (or `design <name>` generates one); writes `previews/art/<name>-design.png`. Commit and stop.
2. Approval — the user looks at the preview and says yes or asks for changes. Record a yes with `art.py approve <name>` (a no with `--reject --note "..."`). Nothing below runs without it; a regenerated design clears approval.
3. `art.py rotate <name>` — turns the approved design into a stored PixelLab character with 8 rotations and downloads the declared directions. Preview: `<name>-rotations.png`.
4. `art.py animate <name> [animation] [--direction d]` — one job per direction per animation; `--direction` redoes one direction and keeps the rest. Preview: `<name>-<animation>.png`, frames numbered.
5. Judge and trim — inspect each sheet; record the frames to keep with `art.py trim <name> <animation> <direction|all> <from> <to>`. Tail frames are the usual failure.
6. `art.py import <name>` — writes `assets/characters/<name>/<animation>.png` (rows are directions) and `assets/characters/<name>/<name>.tres`, a SpriteFrames whose animations are named `<animation>_<direction>` plus `stand_<direction>` from the rotations.
7. Wire — an `AnimatedSprite2D` in the character's scene plays animations by name.

## What works

- Prompts end with "alone, centered, no props, no base, nothing else in frame" and, above 64 px, "full body from the top of the hat to the soles of the boots"; a square canvas of 128 or more returns busts, a tall one (72×128) returns figures.
- Variants that share a seed and view line up pixel for pixel, so a feature (eyes, hat) can be copied between them with PIL when the edit model overdoes it. The edit model enlarges features unless told "same size and shape".
- The user judges faces from an 8× close-up and sprites from a 2× or 3× sheet.
- `breathing-idle` template for idle; a custom "breathing" prompt invents gestures. Check every direction for a frame showing the wrong side and overwrite it with a neighbour.
- A front-facing walk turns to profile unless the action reads "walking straight toward the camera, front view, face and chest toward the viewer in every frame, never turning sideways". The walk template turns too.
- Costs (confirm with `balance`): 1 generation per design, candidate, edit, rotation set, and per animation direction.

## Tiles

Declare the terrain pair in `tiles.json`: prompts, `tile_size`, `seed`, PixelLab `params` (use `"mode": "pro"`; the standard mode gives flat grass and gridded soil), `edge_blend` (pixels faded toward the flat terrain colour at every tile edge, which is what hides seams), `soften_upper` (pulls the upper terrain toward its mean so furrows stay faint), `field_colour` and `field_flatten` (the untilled look, derived from the upper tiles so edges stay aligned), and per-season `lower` prompts, `lower_colour` (the flat plain tile and the shift applied to the textured tiles) and `variants`. With `"variant_mode": "sprite"` each variant prompt becomes a `variant_size` transparent sprite dropped at a seeded offset onto the flat lower colour; without it the prompt is inpainted into the centre of the textured tile, which keeps texture around it. Then `art.py tile-design <name> [--season s] [--variants-only]` (one generation per tileset and per variant; the preview stacks a sample field per season with a tilled patch inside it), approval as above, and `art.py tile-import <name>`, which writes `assets/tiles/<name>_<season>.png` and its `.tres`. Atlas rows 0-3 are the Wang tiles ordered by corner mask NW NE SW SE (lower ↔ untilled field, index 0 flat), row 4 the variants, rows 5-8 the same Wang shapes as tilled cutouts and rows 9-12 as white masks. `scripts/farm/farm.gd` draws the field, the tilled cutouts, and the watered masks (multiplied brown) each on a dual grid, swaps the season's TileSet, and scatters variants.

## Placeholders

Small hand-authored pixel art is a string grid under `grids/`: `@out` names the PNG, `@at col row` places the grid inside it, `@scale n` upscales, `@<char> #rrggbb|none` defines the palette, and every other line is a row of pixels. `art.py placeholders` converts every grid and writes the resources listed in `placeholders.json`.
