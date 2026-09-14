extends TestCase
## Guards the JSON and text files under data/ against entries the game would misread.

const SEASONS: Array[String] = ["spring", "summer", "autumn", "winter"]
const GRASS_DIALS: Array[String] = ["coverage", "clumpiness", "flowers"]


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
	var seasons: Dictionary = data.get("seasons", {})
	for season: String in SEASONS:
		check(seasons.has(season), season + " has grass dials")
	var presets: Dictionary = data.get("presets", {})
	for group: Dictionary in [seasons, presets]:
		for name: String in group:
			var dials: Dictionary = group[name]
			for dial: String in GRASS_DIALS:
				var value: float = dials.get(dial, -1.0)
				check(value >= 0.0 and value <= 1.0, "%s.%s is a fraction" % [name, dial])
	for name: String in presets:
		var preset: Dictionary = presets[name]
		check(preset.has("day"), name + " preset names a day")


func test_farm_map() -> void:
	var rows: PackedStringArray = FileAccess.get_file_as_string("res://data/maps/farm.txt").strip_edges().split("\n")
	var farm_script: GDScript = load("res://scripts/farm/farm.gd")
	var known: Dictionary = farm_script.get_script_constant_map()["MAP_CHARS"]
	var counts: Dictionary[String, int] = {}
	check(rows.size() > 0, "map has rows")
	for row: String in rows:
		check_eq(row.length(), rows[0].length(), "rows are the same width")
		for symbol: String in row:
			counts[symbol] = counts.get(symbol, 0) + 1
			check(known.has(symbol) or symbol == "P", "unknown map symbol '%s'" % symbol)
	check_eq(counts.get("P", 0), 1, "exactly one player start")
	check_eq(counts.get("B", 0), 1, "exactly one bed")
	check(counts.get("s", 0) as int > 0, "some field to farm")


func _json(path: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}
