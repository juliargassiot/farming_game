class_name GameState
extends Node

const SAVE_PATH: String = "user://save.json"

var day: int = 1
var money: int = 0
var plots: Dictionary[Vector2i, Plot] = {}
var unlocks: Array[String] = []
var crops: Dictionary[String, CropData] = {}


func _init() -> void:
	crops = CropData.load_all()


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func new_game() -> void:
	day = 1
	money = 0
	plots.clear()
	unlocks.clear()


func plot_at(cell: Vector2i) -> Plot:
	if not plots.has(cell):
		plots[cell] = Plot.new()
	return plots[cell]


func seed_for(season: String) -> CropData:
	for crop_id: String in crops:
		if crops[crop_id].grows_in(season) and is_unlocked(crops[crop_id].requires):
			return crops[crop_id]
	return null


func is_unlocked(requirement: String) -> bool:
	return requirement == "" or unlocks.has(requirement)


func advance_day() -> void:
	day += 1
	for cell: Vector2i in plots:
		plots[cell].advance_day()


func save() -> void:
	var saved_plots: Dictionary = {}
	for cell: Vector2i in plots:
		saved_plots["%d,%d" % [cell.x, cell.y]] = plots[cell].to_dict()
	var file: FileAccess = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify({"day": day, "money": money, "plots": saved_plots, "unlocks": unlocks}))


func load_game() -> bool:
	if not has_save():
		return false
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if not parsed is Dictionary:
		return false
	var data: Dictionary = parsed
	day = data.get("day", 1)
	money = data.get("money", 0)
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
