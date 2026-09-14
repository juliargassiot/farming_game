extends Node2D
## The overworld scene: draws the map, follows the farmer, names the region underfoot, and works the farm plots.

const ACTION_HINTS: Dictionary[Plot.Action, String] = {
	Plot.Action.TILL: "A: Till", Plot.Action.PLANT: "A: Plant", Plot.Action.WATER: "A: Water", Plot.Action.HARVEST: "A: Harvest",
}
const TERRAIN_SETS: Dictionary[String, String] = {
	"spring": "res://assets/tiles/grass_soil_spring.tres", "summer": "res://assets/tiles/grass_soil_summer.tres",
	"autumn": "res://assets/tiles/grass_soil_autumn.tres", "winter": "res://assets/tiles/grass_soil_winter.tres",
}

@export_file("*.txt") var map_path: String = WorldMap.MAP_PATH
@export var grass_preset: String = ""

var map: WorldMap
var season: String = ""

@onready var terrain: TileMapLayer = $Terrain
@onready var tilled_layer: TileMapLayer = $Tilled
@onready var ground: TileMapLayer = $Ground
@onready var wet: TileMapLayer = $Wet
@onready var crop_layer: TileMapLayer = $Crops
@onready var player: Player = $Player
@onready var camera: Camera2D = $Player/Camera
@onready var status: Label = $HUD/Status
@onready var region_label: Label = $HUD/Region
@onready var hint: Label = $HUD/Hint


func _ready() -> void:
	map = WorldMap.load_files(map_path)
	_build_map()
	_refresh_plots()
	player.interact.connect(_on_interact)
	player.entered_cell.connect(_on_entered_cell)
	_show_region(player.cell)


func _process(_delta: float) -> void:
	status.text = "%s    $%d" % [Calendar.label(Game.day), Game.money]
	hint.text = _hint_for(player.target_cell())
	if Input.is_action_just_pressed("cancel"):
		Game.save()
		get_tree().change_scene_to_file("res://scenes/title/title.tscn")


func _build_map() -> void:
	camera.limit_right = map.size.x * Player.TILE
	camera.limit_bottom = map.size.y * Player.TILE
	if map.start.x >= 0:
		player.place_at_cell(map.start)
	for y: int in map.size.y:
		for x: int in map.size.x:
			var cell: Vector2i = Vector2i(x, y)
			var kind: WorldMap.Ground = map.ground_at(cell)
			if kind != WorldMap.Ground.GRASS and kind != WorldMap.Ground.FIELD:
				ground.set_cell(cell, 0, Vector2i(kind, 0))


func _refresh_plots() -> void:
	var wanted: String = Calendar.season_key(Game.day)
	if wanted != season:
		season = wanted
		terrain.tile_set = load(TERRAIN_SETS[season])
		tilled_layer.tile_set = terrain.tile_set
		wet.tile_set = terrain.tile_set
		_paint_grass()
	var tilled: Dictionary[Vector2i, bool] = {}
	var watered: Dictionary[Vector2i, bool] = {}
	for cell: Vector2i in map.farmable:
		var plot: Plot = Game.plots.get(cell)
		if plot != null and plot.tilled:
			tilled[cell] = true
			if plot.watered:
				watered[cell] = true
		if plot != null and plot.tilled and plot.crop != null:
			crop_layer.set_cell(cell, 0, Vector2i(plot.crop.atlas_column(plot.stage()), plot.crop.atlas_row))
		else:
			crop_layer.erase_cell(cell)
	var bounds: Rect2i = map.farm_bounds()
	TerrainPainter.paint(tilled_layer, tilled, TerrainPainter.TILLED_ROW, bounds, false)
	TerrainPainter.paint(wet, watered, TerrainPainter.WET_ROW, bounds, false)


func _paint_grass() -> void:
	var open: Array[Vector2i] = []
	for cell: Vector2i in TerrainPainter.paint(terrain, map.farmable, 0, Rect2i(Vector2i.ZERO, map.size + Vector2i.ONE), true):
		if _open_around(cell):
			open.append(cell)
	var assigned: Dictionary[Vector2i, int] = Grass.load_dials(season, grass_preset).assign(open)
	for cell: Vector2i in open:
		if assigned[cell] != Grass.PLAIN:
			terrain.set_cell(cell, 0, TerrainPainter.variant_coords(cell, assigned[cell]))


func _open_around(cell: Vector2i) -> bool:
	for corner: Vector2i in [Vector2i(cell.x - 1, cell.y - 1), Vector2i(cell.x, cell.y - 1), Vector2i(cell.x - 1, cell.y), cell]:
		if ground.get_cell_source_id(corner) != -1:
			return false
	return true


func _on_entered_cell(cell: Vector2i, direction: Vector2i) -> void:
	_show_region(cell)
	var feet: Vector2 = player.position + Vector2(0, 6)
	var under: Vector2i = terrain.local_to_map(terrain.to_local(feet))
	if not TerrainPainter.is_textured(terrain.get_cell_atlas_coords(under)):
		return
	var sway_direction: float = signf(direction.x) if direction.x != 0 else (1.0 if (cell.x + cell.y) % 2 == 0 else -1.0)
	var sway: GrassSway = GrassSway.spawn(self, terrain.tile_set, Vector2i.ZERO, terrain.get_cell_atlas_coords(under), terrain.to_global(terrain.map_to_local(under)), sway_direction)
	move_child(sway, terrain.get_index() + 1)


func _show_region(cell: Vector2i) -> void:
	var region: WorldMap.Region = map.region_at(cell)
	region_label.text = region.display_name if region != null else ""


func _hint_for(cell: Vector2i) -> String:
	if cell == map.bed:
		return "A: Sleep"
	if not map.farmable.has(cell):
		return "B: Save and quit to title"
	var action: Plot.Action = Game.plot_at(cell).next_action(Game.seed_for(Calendar.season_key(Game.day)))
	return ACTION_HINTS.get(action, "")


func _on_interact(cell: Vector2i) -> void:
	if cell == map.bed:
		Game.advance_day()
		Game.save()
	elif map.farmable.has(cell):
		var plot: Plot = Game.plot_at(cell)
		var seed: CropData = Game.seed_for(Calendar.season_key(Game.day))
		Game.money += plot.apply(plot.next_action(seed), seed)
	_refresh_plots()
