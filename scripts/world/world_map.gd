class_name WorldMap
extends RefCounted
## The overworld as data: a text grid of ground symbols and the named regions laid over it.

enum Ground {
	GRASS, SOIL, SOIL_WET, WATER, FENCE, PATH, BED, FIELD, SAND, SEA, ROCK, CRAG, CAVE, MINE, MARSH, BOG, DEAD_TREE, TREE, TALLGRASS, COBBLE, HOUSE, DOCK, ROOF, DOOR, BED_FOOT, BLOCK, LEDGE, TRAIL,
}

const MAP_PATH: String = "res://data/maps/world.txt"
const REGIONS_PATH: String = "res://data/world.json"
const SYMBOLS: Dictionary[String, Ground] = {
	".": Ground.GRASS, "s": Ground.FIELD, "~": Ground.WATER, "#": Ground.FENCE, "=": Ground.PATH, "B": Ground.BLOCK, "P": Ground.GRASS,
	",": Ground.SAND, "w": Ground.SEA, "^": Ground.ROCK, "M": Ground.CRAG, "c": Ground.CAVE, "m": Ground.MINE, "%": Ground.MARSH,
	":": Ground.BOG, "t": Ground.DEAD_TREE, "T": Ground.TREE, "\"": Ground.TALLGRASS, "+": Ground.COBBLE, "H": Ground.HOUSE, "D": Ground.DOCK,
	"R": Ground.ROOF, "d": Ground.DOOR, "b": Ground.BED_FOOT, "X": Ground.BLOCK, "r": Ground.LEDGE, "-": Ground.TRAIL,
}
const SOLID: Array[Ground] = [
	Ground.WATER, Ground.FENCE, Ground.BED, Ground.SEA, Ground.ROCK, Ground.CRAG, Ground.MARSH, Ground.DEAD_TREE, Ground.TREE, Ground.HOUSE,
	Ground.ROOF, Ground.BED_FOOT, Ground.BLOCK,
]
const STEPS: Array[Vector2i] = [Vector2i.RIGHT, Vector2i.LEFT, Vector2i.DOWN, Vector2i.UP]


class Region:
	var id: String = ""
	var display_name: String = ""
	var race: String = ""
	var kind: String = ""
	var rect: Rect2i = Rect2i()
	var combat_zone: bool = false
	var tree: String = "oak"
	var dead_tree: String = "dead"

	static func from_dict(region_id: String, data: Dictionary) -> Region:
		var region: Region = Region.new()
		region.id = region_id
		region.display_name = data.get("name", region_id)
		region.race = data.get("race", "")
		region.kind = data.get("kind", "")
		region.combat_zone = data.get("combat_zone", false)
		region.tree = data.get("tree", region.tree)
		region.dead_tree = data.get("dead_tree", region.dead_tree)
		var bounds: Array = data.get("rect", [0, 0, 0, 0])
		var left: int = bounds[0]
		var top: int = bounds[1]
		var right: int = bounds[2]
		var bottom: int = bounds[3]
		region.rect = Rect2i(left, top, right - left, bottom - top)
		return region


var rows: PackedStringArray = PackedStringArray()
var size: Vector2i = Vector2i.ZERO
var start: Vector2i = Vector2i(-1, -1)
var beds: Dictionary[Vector2i, bool] = {}
var farmable: Dictionary[Vector2i, bool] = {}
var buildings: Dictionary[Vector2i, String] = {}
var regions: Array[Region] = []


static func load_files(map_path: String = MAP_PATH, regions_path: String = REGIONS_PATH) -> WorldMap:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(regions_path))
	var data: Dictionary = parsed if parsed is Dictionary else {}
	return from_text(FileAccess.get_file_as_string(map_path), data)


static func from_text(text: String, data: Dictionary = {}) -> WorldMap:
	"""data holds "regions" (id -> region fields) and "buildings" ("x,y" anchor -> prop name)."""
	var map: WorldMap = WorldMap.new()
	map.rows = text.strip_edges().split("\n")
	map.size = Vector2i(map.rows[0].length(), map.rows.size())
	for y: int in map.rows.size():
		for x: int in map.rows[y].length():
			var symbol: String = map.rows[y][x]
			if symbol == "P":
				map.start = Vector2i(x, y)
			elif symbol == "B" or symbol == "b":
				map.beds[Vector2i(x, y)] = true
			elif symbol == "s":
				map.farmable[Vector2i(x, y)] = true
	var region_data: Dictionary = data.get("regions", {})
	for region_id: String in region_data:
		var entry: Dictionary = region_data[region_id]
		map.regions.append(Region.from_dict(region_id, entry))
	var building_data: Dictionary = data.get("buildings", {})
	for key: String in building_data:
		var parts: PackedStringArray = key.split(",")
		map.buildings[Vector2i(int(parts[0]), int(parts[1]))] = building_data[key]
	return map


func in_bounds(cell: Vector2i) -> bool:
	return cell.x >= 0 and cell.y >= 0 and cell.x < size.x and cell.y < rows.size() and cell.x < rows[cell.y].length()


func symbol_at(cell: Vector2i) -> String:
	return rows[cell.y][cell.x] if in_bounds(cell) else ""


func ground_at(cell: Vector2i) -> Ground:
	var symbol: String = symbol_at(cell)
	return SYMBOLS[symbol] if SYMBOLS.has(symbol) else Ground.GRASS


func is_walkable(cell: Vector2i) -> bool:
	return in_bounds(cell) and not SOLID.has(ground_at(cell))


func region_at(cell: Vector2i) -> Region:
	for region: Region in regions:
		if region.rect.has_point(cell):
			return region
	return null


func farm_bounds() -> Rect2i:
	var bounds: Rect2i = Rect2i()
	for cell: Vector2i in farmable:
		bounds = Rect2i(cell, Vector2i.ONE) if bounds.size == Vector2i.ZERO else bounds.expand(cell)
	return bounds.grow_individual(0, 0, 1, 1) if bounds.size != Vector2i.ZERO else bounds


func reachable_from(origin: Vector2i) -> Dictionary[Vector2i, bool]:
	var seen: Dictionary[Vector2i, bool] = {origin: true}
	var queue: Array[Vector2i] = [origin]
	var head: int = 0
	while head < queue.size():
		var cell: Vector2i = queue[head]
		head += 1
		for step: Vector2i in STEPS:
			var next: Vector2i = cell + step
			if is_walkable(next) and not seen.has(next):
				seen[next] = true
				queue.append(next)
	return seen
