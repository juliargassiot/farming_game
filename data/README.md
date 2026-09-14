# Data

`grass.json` steers where textured grass and flowers appear. `seasons` holds the live dials per season; `presets` are named alternatives for look sheets. `tools/grass_sheet.sh` renders every preset on `maps/grass_strip.txt` into `previews/grass-sheet.png`; the user picks by letter and describes changes in words, which become dial edits under `seasons`.

`maps/world.txt` is the whole overworld, one character per tile (legend in `scripts/world/world_map.gd`); `world.json` names each district, its race, and its tile rectangle. `tools/world_overview.py` draws both into `previews/world-overview.png`, and `tools/screenshot.sh scenes/world/world.tscn <name> <x,y>` renders any spot at play scale.

`trees.json` is one entry per tree kind: the prop it draws, whether it chops for a wood (each race's wood feeds its own furniture later) or shakes for fruit, and the driftwood that washes up on the coast instead.
