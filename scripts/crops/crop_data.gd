class_name CropData
extends RefCounted

var id: String = ""
var display_name: String = ""
var seasons: Array[String] = []
var stage_days: Array[int] = []
var sell_price: int = 0
var atlas_row: int = 0
var stage_columns: Array[int] = []
var regrow_days: int = 0
var trellis: bool = false
var variants: Array[String] = []
var yield_count: int = 1
var requires: String = ""
var kind: String = "crop"
var favoured_by: String = ""


static func from_dict(crop_id: String, d: Dictionary) -> CropData:
	var crop: CropData = CropData.new()
	crop.id = crop_id
	crop.display_name = d.get("name", crop_id)
	for season: String in d.get("seasons", []):
		crop.seasons.append(season)
	for days: float in d.get("stage_days", []):
		crop.stage_days.append(int(days))
	for variant: String in d.get("variants", []):
		crop.variants.append(variant)
	crop.sell_price = d.get("sell_price", 0)
	crop.atlas_row = d.get("atlas_row", 0)
	crop.regrow_days = d.get("regrow_days", 0)
	crop.trellis = d.get("trellis", false)
	crop.yield_count = d.get("yield", 1)
	crop.requires = d.get("requires", "")
	crop.kind = d.get("kind", "crop")
	crop.favoured_by = d.get("favoured_by", "")
	return crop


static func load_all(path: String = "res://data/crops.json", atlas_path: String = "res://data/crop_atlas.json") -> Dictionary[String, CropData]:
	var result: Dictionary[String, CropData] = {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	var atlas: Variant = JSON.parse_string(FileAccess.get_file_as_string(atlas_path)) if FileAccess.file_exists(atlas_path) else {}
	if parsed is Dictionary:
		var table: Dictionary = parsed
		var layout: Dictionary = atlas if atlas is Dictionary else {}
		for crop_id: String in table:
			var entry: Dictionary = table[crop_id]
			result[crop_id] = from_dict(crop_id, entry)
			if layout.has(crop_id):
				var crop_layout: Dictionary = layout[crop_id]
				result[crop_id].apply_layout(crop_layout)
	return result


func apply_layout(layout: Dictionary) -> void:
	var row: float = layout.get("row", 0)
	atlas_row = int(row)
	var starts: Dictionary = layout.get("stages", {})
	stage_columns.clear()
	for stage_name: String in ["seed", "sprout", "growing", "ready"]:
		if starts.has(stage_name):
			var column: float = starts[stage_name]
			stage_columns.append(int(column))


func atlas_column(stage_index: int) -> int:
	if stage_columns.is_empty():
		return stage_index
	var art_stage: int = mini(stage_index, 3) if stage_index < stage_days.size() else 3
	return stage_columns[mini(art_stage, stage_columns.size() - 1)]


func total_days() -> int:
	var total: int = 0
	for days: int in stage_days:
		total += days
	return total


func grows_in(season: String) -> bool:
	return seasons.is_empty() or seasons.has(season)


func stage_for(days_grown: int) -> int:
	var remaining: int = days_grown
	for i: int in stage_days.size():
		if remaining < stage_days[i]:
			return i
		remaining -= stage_days[i]
	return stage_days.size()


func is_mature(days_grown: int) -> bool:
	return days_grown >= total_days()


func harvest_name(variant: int) -> String:
	return variants[variant] if variant >= 0 and variant < variants.size() else display_name
