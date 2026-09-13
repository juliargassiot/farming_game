extends TestCase


func test_data_loads() -> void:
	check(game.crops.size() >= 3, "crops.json has at least three crops")
	for crop_id: String in game.crops:
		var crop: CropData = game.crops[crop_id]
		check(crop.stage_days.size() > 0, crop_id + " has growth stages")
		check(crop.sell_price > 0, crop_id + " sells for something")
		check(crop.seasons.size() > 0, crop_id + " has a season")


func test_growth_stages() -> void:
	var crop: CropData = CropData.from_dict("x", {"stage_days": [2, 1], "sell_price": 5, "seasons": ["spring"]})
	check_eq(crop.total_days(), 3, "total days")
	check_eq(crop.stage_for(0), 0, "day 0 stage")
	check_eq(crop.stage_for(1), 0, "day 1 stage")
	check_eq(crop.stage_for(2), 1, "day 2 stage")
	check_eq(crop.stage_for(3), 2, "mature stage index")
	check(crop.is_mature(3), "mature after total days")
	check(not crop.is_mature(2), "not mature before total days")


func test_seed_for_season() -> void:
	check_eq(game.seed_for("spring").id, "turnip", "spring seed")
	check(game.seed_for("winter") == null, "no winter seed")
