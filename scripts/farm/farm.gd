extends Node2D

enum Ground { GRASS, SOIL, SOIL_WET, WATER, FENCE, PATH, BED, FIELD }
enum Terrain { GRASS, SOIL }

const MAP_PATH: String = "res://data/maps/farm.txt"
const MAP_CHARS: Dictionary[String, Ground] = {
	".": Ground.GRASS, "s": Ground.FIELD, "~": Ground.WATER, "#": Ground.FENCE, "=": Ground.PATH, "B": Ground.BED,
}
const TERRAIN_SETS: Dictionary[String, String] = {
	"spring": "res://assets/tiles/grass_soil_spring.tres", "summer": "res://assets/tiles/grass_soil_summer.tres",
	"autumn": "res://assets/tiles/grass_soil_autumn.tres", "winter": "res://assets/tiles/grass_soil_winter.tres",
}
const VARIANT_ROW: int = 4
const VARIANT_CHANCE: float = 0.3
const ACTION_HINTS: Dictionary[Plot.Action, String] = {
	Plot.Action.TILL: "A: Till", Plot.Action.PLANT: "A: Plant", Plot.Action.WATER: "A: Water", Plot.Action.HARVEST: "A: Harvest",
}

var bed_cell: Vector2i = Vector2i(-1, -1)
var farmable: Dictionary[Vector2i, bool] = {}
var open_cells: Array[Vector2i] = []
var season: String = ""

@onready var terrain: TileMapLayer = $Terrain
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
	camera.limit_right = rows[0].length() * Player.TILE
	camera.limit_bottom = rows.size() * Player.TILE
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
			if kind == Ground.GRASS or kind == Ground.FIELD:
				open_cells.append(cell)
			else:
				ground.set_cell(cell, 0, Vector2i(kind, 0))


func _refresh_plots() -> void:
	var wanted: String = Calendar.season_key(Game.day)
	if wanted != season:
		season = wanted
		terrain.tile_set = load(TERRAIN_SETS[season])
	var soil: Array[Vector2i] = []
	for cell: Vector2i in farmable:
		var plot: Plot = Game.plots.get(cell)
		var tilled: bool = plot != null and plot.tilled
		if tilled:
			soil.append(cell)
		if tilled and plot.watered:
			wet.set_cell(cell, 0, Vector2i.ZERO)
		else:
			wet.erase_cell(cell)
		if tilled and plot.crop != null:
			crop_layer.set_cell(cell, 0, Vector2i(plot.stage(), plot.crop.atlas_row))
		else:
			crop_layer.erase_cell(cell)
	terrain.set_cells_terrain_connect(open_cells, 0, Terrain.GRASS)
	terrain.set_cells_terrain_connect(soil, 0, Terrain.SOIL)
	_scatter_variants(soil)


func _scatter_variants(soil: Array[Vector2i]) -> void:
	var source: TileSetAtlasSource = terrain.tile_set.get_source(0)
	var variants: int = source.get_atlas_grid_size().x if source.get_atlas_grid_size().y > VARIANT_ROW else 0
	for cell: Vector2i in open_cells:
		var plain: bool = true
		for dy: int in range(-1, 2):
			for dx: int in range(-1, 2):
				if soil.has(cell + Vector2i(dx, dy)):
					plain = false
		var roll: int = hash(cell) % 100
		if plain and variants > 0 and roll < int(VARIANT_CHANCE * 100):
			var variant: int = (hash(cell * 7) % variants + variants) % variants
			if source.has_tile(Vector2i(variant, VARIANT_ROW)):
				terrain.set_cell(cell, 0, Vector2i(variant, VARIANT_ROW))


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
