extends TestCase
## Guards the JSON and text files under data/ against entries the game would misread.

const SEASONS: Array[String] = ["spring", "summer", "autumn", "winter"]
const GRASS_DIALS: Array[String] = ["seed", "patch_size", "light_above", "dark_below", "stamp_step", "stamp_density", "bleed"]


func test_crops_json() -> void:
	var table: Dictionary = _json("res://data/crops.json")
	check(not table.is_empty(), "crops.json parses to an object")
	var atlas_rows: Dictionary[int, String] = {}
	for crop_id: String in table:
		var entry: Dictionary = table[crop_id]
		var crop: CropData = CropData.from_dict(crop_id, entry)
		check(crop.display_name != crop_id, crop_id + " has a display name")
		for season: String in crop.seasons:
			check(SEASONS.has(season), "%s season '%s' is unknown" % [crop_id, season])
		for days: int in crop.stage_days:
			check(days > 0, crop_id + " stage lasts at least a day")
		check(crop.regrow_days <= crop.total_days(), crop_id + " regrows within its growth time")
		check(crop.yield_count >= 1, crop_id + " yields at least one")
		check(crop.variants.is_empty() or crop.variants.size() >= 2, crop_id + " variants need two or more forms")
		if entry.has("atlas_row"):
			check(not atlas_rows.has(crop.atlas_row), "%s shares atlas row %d with %s" % [crop_id, crop.atlas_row, atlas_rows.get(crop.atlas_row, "")])
			atlas_rows[crop.atlas_row] = crop_id


func test_grass_json() -> void:
	var data: Dictionary = _json("res://data/grass.json")
	var dials: Dictionary = data.get("dials", {})
	for dial: String in GRASS_DIALS:
		check(dials.has(dial), dial + " dial is set")
	var seasons: Dictionary = data.get("seasons", {})
	for season: String in SEASONS:
		check(seasons.has(season), season + " has a palette")
		var palette: Dictionary = seasons.get(season, {})
		for tone: String in ["dark", "mid", "light"]:
			var shades: Array = palette.get(tone, [])
			check_eq(shades.size(), 3, "%s %s has three shades" % [season, tone])
			for shade: Variant in shades:
				check(Color.html_is_valid(str(shade)), "%s %s shade %s is a colour" % [season, tone, str(shade)])


func test_world_map() -> void:
	var rows: PackedStringArray = FileAccess.get_file_as_string(WorldMap.MAP_PATH).strip_edges().split("\n")
	var counts: Dictionary[String, int] = {}
	check(rows.size() > 0, "map has rows")
	for row: String in rows:
		check_eq(row.length(), rows[0].length(), "rows are the same width")
		for symbol: String in row:
			counts[symbol] = counts.get(symbol, 0) + 1
			check(WorldMap.SYMBOLS.has(symbol), "unknown map symbol '%s'" % symbol)
	check_eq(counts.get("P", 0), 1, "exactly one player start")
	check_eq(counts.get("B", 0), 1, "exactly one bed, the farmhouse door for now")

	check(counts.get("s", 0) as int > 0, "some field to farm")


func test_world_regions() -> void:
	var map: WorldMap = WorldMap.load_files()
	var reachable: Dictionary[Vector2i, bool] = map.reachable_from(map.start)
	check(map.regions.size() >= 8, "the world names its districts")
	for region: WorldMap.Region in map.regions:
		check(region.display_name != "", region.id + " has a name")
		check(Rect2i(Vector2i.ZERO, map.size).encloses(region.rect), region.id + " lies inside the map")
		for other: WorldMap.Region in map.regions:
			check(other == region or not region.rect.intersects(other.rect), "%s overlaps %s" % [region.id, other.id])
		if region.kind == "sea":
			continue
		var found: bool = false
		for cell: Vector2i in reachable:
			if region.rect.has_point(cell):
				found = true
				break
		check(found, region.id + " can be reached on foot from the farm")
	check(map.region_at(map.start) != null and map.region_at(map.start).kind == "farm", "the farmer starts on the farm")
	for bed: Vector2i in map.beds:
		check(map.region_at(bed) == map.region_at(map.start), "the bed is on the farm")
		var beside: bool = false
		for step: Vector2i in WorldMap.STEPS:
			beside = beside or reachable.has(bed + step)
		check(beside, "the farmer can stand beside the bed")


func test_props_json() -> void:
	var props: Dictionary = _json("res://data/props.json")
	var map: WorldMap = WorldMap.load_files()
	check(map.buildings.values().has("farmhouse"), "the farmhouse is placed")
	for cell: Vector2i in map.buildings:
		check(props.has(map.buildings[cell]), map.buildings[cell] + " is imported")
		check(map.ground_at(cell) == WorldMap.Ground.BLOCK, "%s anchors on a solid footprint cell" % map.buildings[cell])
	check(props.has("oak") and props.has("dead"), "props.json has the oak and the dead tree")
	for name: String in props:
		var box: Array = props[name]
		var width: int = box[2] if box.size() == 4 else 0
		var height: int = box[3] if box.size() == 4 else 0
		check(width > 0 and height > 0, name + " is an x, y, width, height box")
	var declared: Dictionary = _json("res://tools/art/props.json")
	for region: WorldMap.Region in map.regions:
		for prop: String in [region.tree, region.dead_tree]:
			check(props.has(prop) or declared.has(prop), "%s prop '%s' is neither imported nor declared" % [region.id, prop])


func test_trees_json() -> void:
	var trees: Dictionary = _json("res://data/trees.json")
	var declared: Dictionary = _json("res://tools/art/props.json")
	var woods: Dictionary[String, String] = {}
	for kind: String in trees:
		if kind.begins_with("_"):
			continue
		var tree: Dictionary = trees[kind]
		check(declared.has(kind), kind + " has prop art declared")
		var chop: bool = tree.get("chop", false)
		check(chop == tree.has("wood") and chop != tree.has("shake"), kind + " either chops for wood or shakes for fruit")
		if chop:
			var wood: Dictionary = tree["wood"]
			var wood_id: String = wood.get("id", "")
			check(not woods.has(wood_id), "%s shares wood '%s' with %s" % [kind, wood_id, woods.get(wood_id, "")])
			woods[wood_id] = kind
	for region: WorldMap.Region in WorldMap.load_files().regions:
		check(trees.has(region.tree), "%s tree '%s' is not in trees.json" % [region.id, region.tree])


func _json(path: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}
