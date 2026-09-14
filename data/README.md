# Data

`grass.json` drives the painted ground: `dials` shape the patches (size, how much of the ground is light or dark, how far edges bleed) and `seasons` give each season's palette of three tones plus flowers. Edit it and run `tools/art/grass_paint.py` to repaint `assets/grass/`; judge the result in the world previews.

`maps/world.txt` is the whole overworld, one character per tile (legend in `scripts/world/world_map.gd`); `world.json` names each district, its race, and its tile rectangle. `tools/world_overview.py` draws both into `previews/world-overview.png`, and `tools/screenshot.sh scenes/world/world.tscn <name> <x,y>` renders any spot at play scale.

`trees.json` is one entry per tree kind: the prop it draws, whether it chops for a wood (each race's wood feeds its own furniture later) or shakes for fruit, and the driftwood that washes up on the coast instead.
