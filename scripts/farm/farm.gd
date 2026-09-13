extends Node2D

enum Ground { GRASS, SOIL, SOIL_WET, WATER, FENCE, PATH, BED, FIELD }

const MAP_PATH: String = "res://data/maps/farm.txt"
const MAP_CHARS: Dictionary[String, Ground] = {
	".": Ground.GRASS, "s": Ground.FIELD, "~": Ground.WATER, "#": Ground.FENCE, "=": Ground.PATH, "B": Ground.BED,
}
const ACTION_HINTS: Dictionary[Plot.Action, String] = {
	Plot.Action.TILL: "A: Till", Plot.Action.PLANT: "A: Plant", Plot.Action.WATER: "A: Water", Plot.Action.HARVEST: "A: Harvest",
}
const TERRAIN_SETS: Dictionary[String, String] = {
	"spring": "res://assets/tiles/grass_soil_spring.tres", "summer": "res://assets/tiles/grass_soil_summer.tres",
	"autumn": "res://assets/tiles/grass_soil_autumn.tres", "winter": "res://assets/tiles/grass_soil_winter.tres",
}
const VARIANT_ROW: int = 4
const VARIANT_CHANCE: float = 0.4
const TILLED_ROW: int = 5
const WET_ROW: int = 9

var bed_cell: Vector2i = Vector2i(-1, -1)
var farmable: Dictionary[Vector2i, bool] = {}
var map_size: Vector2i = Vector2i.ZERO
var season: String = ""

@onready var terrain: TileMapLayer = $Terrain
@onready var tilled_layer: TileMapLayer = $Tilled
@onready var ground: TileMapLayer = $Ground
@onready var wet: TileMapLayer = $Wet
@onready var crop_layer: TileMapLayer = $Crops
@onready var player: Player = $Player
@onready var camera: Camera2D = $Player/Camera
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
	map_size = Vector2i(rows[0].length(), rows.size())
	camera.limit_right = map_size.x * Player.TILE
	camera.limit_bottom = map_size.y * Player.TILE
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
			var kind: Ground = MAP_CHARS[symbol] if MAP_CHARS.has(symbol) else Ground.GRASS
			if kind != Ground.GRASS and kind != Ground.FIELD:
				ground.set_cell(cell, 0, Vector2i(kind, 0))


func _refresh_plots() -> void:
	var wanted: String = Calendar.season_key(Game.day)
	if wanted != season:
		season = wanted
		terrain.tile_set = load(TERRAIN_SETS[season])
		tilled_layer.tile_set = terrain.tile_set
		wet.tile_set = terrain.tile_set
		var field_cells: Array[Vector2i] = []
		field_cells.assign(farmable.keys())
		_paint_dual(terrain, field_cells, 0, true)
	var tilled: Array[Vector2i] = []
	var watered: Array[Vector2i] = []
	for cell: Vector2i in farmable:
		var plot: Plot = Game.plots.get(cell)
		if plot != null and plot.tilled:
			tilled.append(cell)
			if plot.watered:
				watered.append(cell)
		if plot != null and plot.tilled and plot.crop != null:
			crop_layer.set_cell(cell, 0, Vector2i(plot.stage(), plot.crop.atlas_row))
		else:
			crop_layer.erase_cell(cell)
	_paint_dual(tilled_layer, tilled, TILLED_ROW, false)
	_paint_dual(wet, watered, WET_ROW, false)


func _paint_dual(layer: TileMapLayer, marked: Array[Vector2i], first_row: int, variants: bool) -> void:
	"""Dual grid: layer cell (i, j) sits half a tile up-left of map cell (i, j); its tile is chosen by which of the four map cells around that point are marked."""
	var source: TileSetAtlasSource = layer.tile_set.get_source(0)
	var variant_count: int = 0
	while variants and source.has_tile(Vector2i(variant_count, VARIANT_ROW)):
		variant_count += 1
	layer.clear()
	for j: int in map_size.y + 1:
		for i: int in map_size.x + 1:
			var index: int = 0
			for corner: Vector2i in [Vector2i(i - 1, j - 1), Vector2i(i, j - 1), Vector2i(i - 1, j), Vector2i(i, j)]:
				index = index * 2 + (1 if marked.has(corner) else 0)
			var cell: Vector2i = Vector2i(i, j)
			if index == 0 and variant_count > 0 and hash(cell) % 100 < int(VARIANT_CHANCE * 100):
				layer.set_cell(cell, 0, Vector2i(hash(cell * 7) % variant_count, VARIANT_ROW))
			elif index > 0 or variants:
				@warning_ignore("integer_division")
				layer.set_cell(cell, 0, Vector2i(index % 4, first_row + index / 4))


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
