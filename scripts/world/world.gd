extends Node2D
## The overworld scene: draws the map, follows the farmer, names the region underfoot, and works the farm plots.

const ACTION_HINTS: Dictionary[Plot.Action, String] = {
	Plot.Action.TILL: "A: Till", Plot.Action.PLANT: "A: Plant", Plot.Action.WATER: "A: Water", Plot.Action.HARVEST: "A: Harvest",
}
const TERRAIN_SETS: Dictionary[String, String] = {
	"spring": "res://assets/tiles/grass_soil_spring.tres", "summer": "res://assets/tiles/grass_soil_summer.tres",
	"autumn": "res://assets/tiles/grass_soil_autumn.tres", "winter": "res://assets/tiles/grass_soil_winter.tres",
}

const PAINTED: Array[WorldMap.Ground] = [WorldMap.Ground.GRASS, WorldMap.Ground.FIELD, WorldMap.Ground.PATH, WorldMap.Ground.COBBLE]
const PROPS: Texture2D = preload("res://assets/tiles/props.png")
const PROPS_PATH: String = "res://data/props.json"
const GRASS_DIR: String = "res://assets/grass/"

@export_file("*.txt") var map_path: String = WorldMap.MAP_PATH

var map: WorldMap
var season: String = ""
var prop_regions: Dictionary[String, Rect2i] = {}
var footprint_ground: Dictionary[Vector2i, WorldMap.Ground] = {}
var grass_sprites: Dictionary[String, Sprite2D] = {}

@onready var grass: Node2D = $Map/Grass
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
@onready var seed_menu: SeedMenu = $HUD/SeedMenu


func _ready() -> void:
	map = WorldMap.load_files(map_path)
	prop_regions = _load_props()
	_build_map()
	_refresh_plots()
	player.interact.connect(_on_interact)
	player.entered_cell.connect(_on_entered_cell)
	seed_menu.closed.connect(func() -> void: player.set_physics_process(true))
	_show_region(player.cell)


func _process(_delta: float) -> void:
	status.text = "%s    $%d" % [Calendar.label(Game.day), Game.money]
	hint.text = _hint_for(player.target_cell())
	if Input.is_action_just_pressed("debug_grow") and map.farmable.has(player.target_cell()):
		Game.plot_at(player.target_cell()).grow_one_stage()
		_refresh_plots()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("seed_menu") and not seed_menu.visible:
		get_viewport().set_input_as_handled()
		player.set_physics_process(false)
		seed_menu.open(Calendar.season_key(Game.day))
		return
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
	for anchor: Vector2i in map.buildings:
		if prop_regions.has(map.buildings[anchor]):
			_place_building(anchor, prop_regions[map.buildings[anchor]])
	for y: int in map.size.y:
		for x: int in map.size.x:
			var cell: Vector2i = Vector2i(x, y)
			var kind: WorldMap.Ground = map.ground_at(cell)
			var prop: String = _prop_for(cell, kind)
			if kind == WorldMap.Ground.BLOCK:
				kind = footprint_ground.get(cell, WorldMap.Ground.GRASS)
			elif prop_regions.has(prop):
				_place_prop(Vector2(cell.x * Player.TILE + Player.TILE / 2.0, (cell.y + 1) * Player.TILE), prop_regions[prop], true)
				kind = _ground_under_prop(cell)
			if not PAINTED.has(kind):
				ground.set_cell(cell, 0, Vector2i(kind, 0))
	_place_grass()


func _place_grass() -> void:
	"""One painted ground image per region (grass and stone paths), under everything else; the season picks the file."""
	for region: WorldMap.Region in map.regions:
		var sprite: Sprite2D = Sprite2D.new()
		sprite.centered = false
		sprite.position = Vector2(region.rect.position * Player.TILE)
		grass.add_child(sprite)
		grass_sprites[region.id] = sprite


func _place_building(anchor: Vector2i, region: Rect2i) -> void:
	"""The sprite stands on its bottom-left anchor cell; one collision box covers the whole footprint."""
	var size: Vector2i = Vector2i(ceili(region.size.x / float(Player.TILE)), ceili(region.size.y / float(Player.TILE)))
	var sprite: Sprite2D = _place_prop(Vector2(anchor.x * Player.TILE + region.size.x / 2.0, (anchor.y + 1) * Player.TILE), region, false)
	var body: StaticBody2D = StaticBody2D.new()
	var shape: CollisionShape2D = CollisionShape2D.new()
	var box: RectangleShape2D = RectangleShape2D.new()
	box.size = Vector2(size * Player.TILE)
	shape.shape = box
	shape.position = Vector2(size.x * Player.TILE / 2.0 - region.size.x / 2.0, -size.y * Player.TILE / 2.0)
	body.add_child(shape)
	sprite.add_child(body)
	var footprint: Rect2i = Rect2i(anchor.x, anchor.y - size.y + 1, size.x, size.y)
	var ground_kind: WorldMap.Ground = _ground_around(footprint)
	for y: int in range(footprint.position.y, footprint.end.y):
		for x: int in range(footprint.position.x, footprint.end.x):
			footprint_ground[Vector2i(x, y)] = ground_kind


func _ground_around(footprint: Rect2i) -> WorldMap.Ground:
	"""The walkable ground most common in the ring just outside a footprint, so a cave in the sand does not sit on grass."""
	var counts: Dictionary[WorldMap.Ground, int] = {}
	var ring: Rect2i = footprint.grow(1)
	for y: int in range(ring.position.y, ring.end.y):
		for x: int in range(ring.position.x, ring.end.x):
			var cell: Vector2i = Vector2i(x, y)
			var kind: WorldMap.Ground = map.ground_at(cell)
			if not footprint.has_point(cell) and map.is_walkable(cell) and kind != WorldMap.Ground.DOOR and kind != WorldMap.Ground.PATH:
				counts[kind] = counts.get(kind, 0) + 1
	var best: WorldMap.Ground = WorldMap.Ground.GRASS
	for kind: WorldMap.Ground in counts:
		if counts[kind] > counts.get(best, 0):
			best = kind
	return best


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


func _place_prop(base: Vector2, region: Rect2i, solid: bool) -> Sprite2D:
	"""A sprite standing on its base point, sorted with the farmer by that y; trees also block the cell there."""
	var texture: AtlasTexture = AtlasTexture.new()
	texture.atlas = PROPS
	texture.region = region
	var sprite: Sprite2D = Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.offset = Vector2(-region.size.x / 2.0, -region.size.y)
	sprite.position = base
	scenery.add_child(sprite)
	if not solid:
		return sprite
	var body: StaticBody2D = StaticBody2D.new()
	var shape: CollisionShape2D = CollisionShape2D.new()
	var box: RectangleShape2D = RectangleShape2D.new()
	box.size = Vector2(Player.TILE, Player.TILE / 2.0)
	shape.shape = box
	shape.position = Vector2(0, -Player.TILE / 4.0)
	body.add_child(shape)
	sprite.add_child(body)
	return sprite


func _refresh_plots() -> void:
	var wanted: String = Calendar.season_key(Game.day)
	if wanted != season:
		season = wanted
		terrain.tile_set = load(TERRAIN_SETS[season])
		tilled_layer.tile_set = terrain.tile_set
		wet.tile_set = terrain.tile_set
		_swap_grass()
	var tilled: Dictionary[Vector2i, bool] = {}
	var watered: Dictionary[Vector2i, bool] = {}
	for cell: Vector2i in map.farmable:
		var plot: Plot = Game.plots.get(cell)
		if plot != null and plot.tilled:
			tilled[cell] = true
			if plot.watered:
				watered[cell] = true
		if plot != null and plot.tilled and plot.crop != null:
			crop_layer.set_cell(cell, 0, Vector2i(plot.crop.atlas_column(plot.stage(), plot.variant), plot.crop.atlas_row))
		else:
			crop_layer.erase_cell(cell)
	var bounds: Rect2i = map.farm_bounds()
	TerrainPainter.paint(terrain, map.farmable, 0, bounds)
	TerrainPainter.paint(tilled_layer, tilled, TerrainPainter.TILLED_ROW, bounds)
	TerrainPainter.paint(wet, watered, TerrainPainter.WET_ROW, bounds)


func _swap_grass() -> void:
	for id: String in grass_sprites:
		var path: String = GRASS_DIR + "%s_%s.png" % [id, season]
		grass_sprites[id].texture = load(path) as Texture2D if ResourceLoader.exists(path) else null


func _on_entered_cell(cell: Vector2i, _direction: Vector2i) -> void:
	_show_region(cell)


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
	_refresh_plots()
