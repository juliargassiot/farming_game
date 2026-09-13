class_name Grass
extends RefCounted
## Decides which open cells carry textured grass and which of those keep flowers, from data/grass.json dials.
## Two noise fields ranked over the whole map make coverage exact and clumps deterministic.

const DATA_PATH: String = "res://data/grass.json"
const PLAIN: int = -1
const FLOWERS: int = 0
const BLADES: int = 1

var coverage: float = 0.4
var clumpiness: float = 0.6
var flowers: float = 0.5


static func load_dials(season: String, preset: String = "") -> Grass:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(DATA_PATH))
	var seasons: Dictionary = data["seasons"]
	var presets: Dictionary = data["presets"]
	var dials: Dictionary = presets[preset] if presets.has(preset) else seasons[season]
	var grass: Grass = Grass.new()
	grass.coverage = dials.get("coverage", grass.coverage)
	grass.clumpiness = dials.get("clumpiness", grass.clumpiness)
	grass.flowers = dials.get("flowers", grass.flowers)
	return grass


func assign(cells: Array[Vector2i]) -> Dictionary[Vector2i, int]:
	var texture_rank: Dictionary[Vector2i, float] = _ranked(cells, 7)
	var textured: Array[Vector2i] = []
	for cell: Vector2i in cells:
		if texture_rank[cell] < coverage:
			textured.append(cell)
	var flower_rank: Dictionary[Vector2i, float] = _ranked(textured, 11)
	var out: Dictionary[Vector2i, int] = {}
	for cell: Vector2i in cells:
		out[cell] = PLAIN
	for cell: Vector2i in textured:
		out[cell] = FLOWERS if flower_rank[cell] < flowers else BLADES
	return out


func _ranked(cells: Array[Vector2i], seed: int) -> Dictionary[Vector2i, float]:
	var noise: FastNoiseLite = FastNoiseLite.new()
	noise.seed = seed
	noise.frequency = lerpf(0.5, 0.05, clumpiness)
	var values: Array[float] = []
	for cell: Vector2i in cells:
		values.append(noise.get_noise_2d(cell.x, cell.y))
	var sorted: Array[float] = values.duplicate()
	sorted.sort()
	var out: Dictionary[Vector2i, float] = {}
	for i: int in cells.size():
		out[cells[i]] = float(sorted.bsearch(values[i])) / maxf(1.0, cells.size())
	return out
