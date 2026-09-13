class_name CropData
extends RefCounted

var id: String = ""
var display_name: String = ""
var seasons: Array[String] = []
var stage_days: Array[int] = []
var sell_price: int = 0
var atlas_row: int = 0


static func from_dict(crop_id: String, d: Dictionary) -> CropData:
	var crop: CropData = CropData.new()
	crop.id = crop_id
	crop.display_name = d.get("name", crop_id)
	for season: String in d.get("seasons", []):
		crop.seasons.append(season)
	for days: float in d.get("stage_days", []):
		crop.stage_days.append(int(days))
	crop.sell_price = d.get("sell_price", 0)
	crop.atlas_row = d.get("atlas_row", 0)
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


func stage_for(days_grown: int) -> int:
	var remaining: int = days_grown
	for stage: int in stage_days.size():
		if remaining < stage_days[stage]:
			return stage
		remaining -= stage_days[stage]
	return stage_days.size()


func is_mature(days_grown: int) -> bool:
	return days_grown >= total_days()


func grows_in(season: String) -> bool:
	return seasons.has(season)
