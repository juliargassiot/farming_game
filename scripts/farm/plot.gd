class_name Plot
extends RefCounted

enum Action { NONE, TILL, PLANT, WATER, HARVEST }

var tilled: bool = false
var watered: bool = false
var crop: CropData = null
var days_grown: int = 0


func next_action(seed: CropData) -> Action:
	if not tilled:
		return Action.TILL
	if crop == null:
		return Action.PLANT if seed != null else Action.NONE
	return Action.HARVEST if crop.is_mature(days_grown) else (Action.NONE if watered else Action.WATER)


func apply(action: Action, seed: CropData) -> int:
	match action:
		Action.TILL:
			tilled = true
		Action.PLANT:
			crop = seed
			days_grown = 0
		Action.WATER:
			watered = true
		Action.HARVEST:
			var earned: int = crop.sell_price
			crop = null
			days_grown = 0
			return earned
	return 0


func advance_day() -> void:
	if crop != null and watered:
		days_grown += 1
	watered = false


func stage() -> int:
	return crop.stage_for(days_grown)


func to_dict() -> Dictionary:
	return {"tilled": tilled, "watered": watered, "crop": crop.id if crop != null else "", "days": days_grown}


static func from_dict(d: Dictionary, crops: Dictionary[String, CropData]) -> Plot:
	var plot: Plot = Plot.new()
	plot.tilled = d.get("tilled", false)
	plot.watered = d.get("watered", false)
	var crop_id: String = d.get("crop", "")
	plot.crop = crops.get(crop_id)
	plot.days_grown = d.get("days", 0)
	return plot
