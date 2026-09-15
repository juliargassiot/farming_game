class_name GameState
extends Node

const SAVE_PATH: String = "user://save.json"

var day: int = 1
var money: int = 0
var plots: Dictionary[Vector2i, Plot] = {}
var unlocks: Array[String] = []
var selected_seed: String = ""
var map_name: String = "world"
var cell: Vector2i = Vector2i(-1, -1)
var facing: Vector2i = Vector2i(0, 1)
var arriving: bool = false
var crops: Dictionary[String, CropData] = {}


func _init() -> void:
	crops = CropData.load_all()


func has_save(path: String = SAVE_PATH) -> bool:
	return FileAccess.file_exists(path)


func new_game() -> void:
	day = 1
	money = 0
	plots.clear()
	unlocks.clear()
	selected_seed = ""
	map_name = "world"
	cell = Vector2i(-1, -1)
	facing = Vector2i(0, 1)
	arriving = false


func travel(exit: WorldMap.Exit) -> void:
	"""The world scene reads these when it next loads and puts the farmer down at the far side of the exit."""
	map_name = exit.map_name
	cell = exit.at
	facing = exit.facing
	arriving = true


func plot_at(cell: Vector2i) -> Plot:
	if not plots.has(cell):
		plots[cell] = Plot.new()
	return plots[cell]


func seed_for(season: String) -> CropData:
	"""The chosen seed if it grows now, else the first that does."""
	var options: Array[CropData] = seeds_for(season)
	for crop: CropData in options:
		if crop.id == selected_seed:
			return crop
	return options[0] if not options.is_empty() else null


func seeds_for(season: String) -> Array[CropData]:
	var options: Array[CropData] = []
	for crop_id: String in crops:
		if crops[crop_id].grows_in(season) and is_unlocked(crops[crop_id].requires):
			options.append(crops[crop_id])
	return options


func is_unlocked(requirement: String) -> bool:
	return requirement == "" or unlocks.has(requirement)


func advance_day() -> void:
	day += 1
	for cell: Vector2i in plots:
		plots[cell].advance_day()


func save(path: String = SAVE_PATH) -> void:
	var saved_plots: Dictionary = {}
	for cell: Vector2i in plots:
		saved_plots["%d,%d" % [cell.x, cell.y]] = plots[cell].to_dict()
	var file: FileAccess = FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify({
			"day": day, "money": money, "plots": saved_plots, "unlocks": unlocks, "seed": selected_seed,
			"map": map_name, "cell": "%d,%d" % [cell.x, cell.y], "facing": Player.DIRECTION_NAMES[facing],
		}))


func load_game(path: String = SAVE_PATH) -> bool:
	if not has_save(path):
		return false
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:
		return false
	var data: Dictionary = parsed
	day = data.get("day", 1)
	money = data.get("money", 0)
	selected_seed = data.get("seed", "")
	map_name = data.get("map", "world")
	var cell_key: String = data.get("cell", "-1,-1")
	var facing_name: String = data.get("facing", "south")
	cell = WorldMap.parse_cell(cell_key)
	facing = Player.DIRECTIONS.get(facing_name, Vector2i(0, 1))
	arriving = false
	plots.clear()
	unlocks.clear()
	for unlock: String in data.get("unlocks", []):
		unlocks.append(unlock)
	var saved_plots: Dictionary = data.get("plots", {})
	for key: String in saved_plots:
		var parts: PackedStringArray = key.split(",")
		var entry: Dictionary = saved_plots[key]
		plots[Vector2i(int(parts[0]), int(parts[1]))] = Plot.from_dict(entry, crops)
	return true
