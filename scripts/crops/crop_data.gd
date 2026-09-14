class_name CropData
extends RefCounted

var id: String = ""
var display_name: String = ""
var seasons: Array[String] = []
var stage_days: Array[int] = []
var sell_price: int = 0
var atlas_row: int = 0
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


static func load_all(path: String = "res://data/crops.json") -> Dictionary[String, CropData]:
	var result: Dictionary[String, CropData] = {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if parsed is Dictionary:
		var table: Dictionary = parsed
		for crop_id: String in table:
			var entry: Dictionary = table[crop_id]
			result[crop_id] = from_dict(crop_id, entry)
	return result


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
