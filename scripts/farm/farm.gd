extends Node2D

enum Ground { GRASS, SOIL, SOIL_WET, WATER, FENCE, PATH, BED, FIELD }

const MAP_PATH: String = "res://data/maps/farm.txt"
const MAP_CHARS: Dictionary[String, Ground] = {
	".": Ground.GRASS, "s": Ground.FIELD, "~": Ground.WATER, "#": Ground.FENCE, "=": Ground.PATH, "B": Ground.BED,
}
const ACTION_HINTS: Dictionary[Plot.Action, String] = {
	Plot.Action.TILL: "A: Till", Plot.Action.PLANT: "A: Plant", Plot.Action.WATER: "A: Water", Plot.Action.HARVEST: "A: Harvest",
}

var bed_cell: Vector2i = Vector2i(-1, -1)
var farmable: Dictionary[Vector2i, bool] = {}

@onready var ground: TileMapLayer = $Ground
@onready var crop_layer: TileMapLayer = $Crops
@onready var player: Player = $Player
@onready var status: Label = $HUD/Status
@onready var hint: Label = $HUD/Hint


func _ready() -> void:
	_build_map()
	_refresh_plots()
	player.interact.connect(_on_interact)


func _process(_delta: float) -> void:
	status.text = "%s    $%d" % [Calendar.label(Game.day), Game.money]
	hint.text = _hint_for(player.target_cell())
	if Input.is_action_just_pressed("cancel"):
		Game.save()
		get_tree().change_scene_to_file("res://scenes/title/title.tscn")


func _build_map() -> void:
	var rows: PackedStringArray = FileAccess.get_file_as_string(MAP_PATH).strip_edges().split("\n")
	for y: int in rows.size():
		for x: int in rows[y].length():
			var cell: Vector2i = Vector2i(x, y)
			var symbol: String = rows[y][x]
			if symbol == "P":
				player.place_at_cell(cell)
			if symbol == "B":
				bed_cell = cell
			if symbol == "s":
				farmable[cell] = true
			_set_ground(cell, MAP_CHARS[symbol] if MAP_CHARS.has(symbol) else Ground.GRASS)


func _set_ground(cell: Vector2i, kind: Ground) -> void:
	ground.set_cell(cell, 0, Vector2i(kind, 0))


func _refresh_plots() -> void:
	for cell: Vector2i in farmable:
		var plot: Plot = Game.plots.get(cell)
		if plot == null or not plot.tilled:
			_set_ground(cell, Ground.FIELD)
			crop_layer.erase_cell(cell)
			continue
		_set_ground(cell, Ground.SOIL_WET if plot.watered else Ground.SOIL)
		if plot.crop == null:
			crop_layer.erase_cell(cell)
		else:
			crop_layer.set_cell(cell, 0, Vector2i(plot.stage(), plot.crop.atlas_row))


func _hint_for(cell: Vector2i) -> String:
	if cell == bed_cell:
		return "A: Sleep"
	if not farmable.has(cell):
		return "B: Save and quit to title"
	var action: Plot.Action = Game.plot_at(cell).next_action(Game.seed_for(Calendar.season_key(Game.day)))
	return ACTION_HINTS.get(action, "")


func _on_interact(cell: Vector2i) -> void:
	if cell == bed_cell:
		Game.advance_day()
		Game.save()
	elif farmable.has(cell):
		var plot: Plot = Game.plot_at(cell)
		var seed: CropData = Game.seed_for(Calendar.season_key(Game.day))
		Game.money += plot.apply(plot.next_action(seed), seed)
	_refresh_plots()
