extends Node2D
## The overworld scene: draws the map, follows the farmer, names the region underfoot, and works the farm plots.

const ACTION_HINTS: Dictionary[Plot.Action, String] = {
	Plot.Action.TILL: "A: Till", Plot.Action.PLANT: "A: Plant", Plot.Action.WATER: "A: Water", Plot.Action.HARVEST: "A: Harvest",
}
const TERRAIN_SETS: Dictionary[String, String] = {
	"spring": "res://assets/tiles/grass_soil_spring.tres", "summer": "res://assets/tiles/grass_soil_summer.tres",
	"autumn": "res://assets/tiles/grass_soil_autumn.tres", "winter": "res://assets/tiles/grass_soil_winter.tres",
}

const PROPS: Texture2D = preload("res://assets/tiles/props.png")
const PROPS_PATH: String = "res://data/props.json"

@export_file("*.txt") var map_path: String = WorldMap.MAP_PATH
@export var grass_preset: String = ""

var map: WorldMap
var season: String = ""
var prop_regions: Dictionary[String, Rect2i] = {}

@onready var terrain: TileMapLayer = $Map/Terrain
@onready var tilled_layer: TileMapLayer = $Map/Tilled
@onready var ground: TileMapLayer = $Map/Ground
@onready var wet: TileMapLayer = $Map/Wet
@onready var crop_layer: TileMapLayer = $Map/Crops
@onready var scenery: Node2D = $Scenery
@onready var player: Player = $Scenery/Player
@onready var camera: Camera2D = $Scenery/Player/Camera
@onready var status: Label = $HUD/Status
@onready var region_label: Label = $HUD/Region
@onready var hint: Label = $HUD/Hint


func _ready() -> void:
	map = WorldMap.load_files(map_path)
	prop_regions = _load_props()
	_build_map()
	_refresh_plots()
	player.interact.connect(_on_interact)
	player.entered_cell.connect(_on_entered_cell)
	_show_region(player.cell)


func _process(_delta: float) -> void:
	status.text = "%s    $%d" % [Calendar.label(Game.day), Game.money]
	hint.text = _hint_for(player.target_cell())
	if Input.is_action_just_pressed("debug_grow") and map.farmable.has(player.target_cell()):
		Game.plot_at(player.target_cell()).grow_one_stage()
		_refresh_plots()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("cancel"):
		get_viewport().set_input_as_handled()
		Game.save()
		get_tree().change_scene_to_file("res://scenes/title/title.tscn")


func _build_map() -> void:
	camera.limit_right = map.size.x * Player.TILE
	camera.limit_bottom = map.size.y * Player.TILE
	player.bounds = Rect2(Vector2(Player.TILE / 2.0, Player.TILE / 2.0), Vector2(map.size) * Player.TILE - Vector2.ONE * Player.TILE)
	if map.start.x >= 0:
		player.place_at_cell(map.start)
	for y: int in map.size.y:
		for x: int in map.size.x:
			var cell: Vector2i = Vector2i(x, y)
			var kind: WorldMap.Ground = map.ground_at(cell)
			var prop: String = _prop_for(cell, kind)
			if prop_regions.has(prop):
				_place_prop(cell, prop_regions[prop])
				kind = _ground_under_prop(cell)
			if kind != WorldMap.Ground.GRASS and kind != WorldMap.Ground.FIELD:
				ground.set_cell(cell, 0, Vector2i(kind, 0))


func _ground_under_prop(cell: Vector2i) -> WorldMap.Ground:
	"""A tree stands on whatever walkable ground its neighbours have most of."""
	var counts: Dictionary[WorldMap.Ground, int] = {}
	for step: Vector2i in WorldMap.STEPS:
		var kind: WorldMap.Ground = map.ground_at(cell + step)
		if map.is_walkable(cell + step) and not prop_regions.has(_prop_for(cell + step, kind)):
			counts[kind] = counts.get(kind, 0) + 1
	var best: WorldMap.Ground = WorldMap.Ground.GRASS
	for kind: WorldMap.Ground in counts:
		if counts[kind] > counts.get(best, 0):
			best = kind
	return best


func _load_props() -> Dictionary[String, Rect2i]:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(PROPS_PATH))
	var data: Dictionary = parsed if parsed is Dictionary else {}
	var out: Dictionary[String, Rect2i] = {}
	for name: String in data:
		var box: Array = data[name]
		var left: int = box[0]
		var top: int = box[1]
		var width: int = box[2]
		var height: int = box[3]
		out[name] = Rect2i(left, top, width, height)
	return out


func _prop_for(cell: Vector2i, kind: WorldMap.Ground) -> String:
	"""Trees take the prop the cell's region names."""
	var region: WorldMap.Region = map.region_at(cell)
	if kind == WorldMap.Ground.TREE:
		return region.tree if region != null else "oak"
	if kind == WorldMap.Ground.DEAD_TREE:
		return region.dead_tree if region != null else "dead"
	return ""


func _place_prop(cell: Vector2i, region: Rect2i) -> void:
	"""A sprite standing on its cell, sorted with the farmer by the y of its base."""
	var texture: AtlasTexture = AtlasTexture.new()
	texture.atlas = PROPS
	texture.region = region
	var sprite: Sprite2D = Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.offset = Vector2(-region.size.x / 2.0, -region.size.y)
	sprite.position = Vector2(cell.x * Player.TILE + Player.TILE / 2.0, (cell.y + 1) * Player.TILE)
	var body: StaticBody2D = StaticBody2D.new()
	var shape: CollisionShape2D = CollisionShape2D.new()
	var box: RectangleShape2D = RectangleShape2D.new()
	box.size = Vector2(Player.TILE, Player.TILE / 2.0)
	shape.shape = box
	shape.position = Vector2(0, -Player.TILE / 4.0)
	body.add_child(shape)
	sprite.add_child(body)
	scenery.add_child(sprite)


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
	var sway: GrassSway = GrassSway.spawn($Map, terrain.tile_set, Vector2i.ZERO, terrain.get_cell_atlas_coords(under), terrain.to_global(terrain.map_to_local(under)), sway_direction)
	$Map.move_child(sway, terrain.get_index() + 1)


func _show_region(cell: Vector2i) -> void:
	var region: WorldMap.Region = map.region_at(cell)
	region_label.text = region.display_name if region != null else ""


func _hint_for(cell: Vector2i) -> String:
	if map.beds.has(cell):
		return "A: Sleep"
	if not map.farmable.has(cell):
		return "B: Save and quit to title"
	var action: Plot.Action = Game.plot_at(cell).next_action(Game.seed_for(Calendar.season_key(Game.day)))
	return ACTION_HINTS.get(action, "")


func _on_interact(cell: Vector2i) -> void:
	if map.beds.has(cell):
		Game.advance_day()
		Game.save()
	elif map.farmable.has(cell):
		var plot: Plot = Game.plot_at(cell)
		var seed: CropData = Game.seed_for(Calendar.season_key(Game.day))
		var action: Plot.Action = plot.next_action(seed)
		Game.money += plot.apply(action, seed)
		if action == Plot.Action.PLANT:
			Game.next_seed()
	_refresh_plots()
