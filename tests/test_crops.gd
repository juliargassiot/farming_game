extends TestCase


func test_data_loads() -> void:
	check(game.crops.size() >= 3, "crops.json has at least three crops")
	for crop_id: String in game.crops:
		var crop: CropData = game.crops[crop_id]
		check(crop.stage_days.size() > 0, crop_id + " has growth stages")
		check(crop.sell_price > 0, crop_id + " sells for something")
		check(crop.seasons.size() > 0 or crop.requires != "", crop_id + " has a season or an unlock")


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
	check_eq(game.seed_for("spring").id, "mandrake", "spring seed")
	check_eq(game.seed_for("winter").id, "moonpetal", "winter seed")
	check(not game.crops["potato"].grows_in("summer") or not game.is_unlocked("root_cellar"), "potato bags wait for the root cellar")
	game.unlocks.append("root_cellar")
	check(game.is_unlocked("root_cellar"), "root cellar unlocks")
	game.unlocks.clear()


func test_fantasy_fields() -> void:
	var sprouts: CropData = game.crops["shifting_sprouts"]
	check_eq(sprouts.variants.size(), 4, "shifting sprouts have four forms")
	check_eq(sprouts.harvest_name(2), "Hare Sprout", "variant name")
	check_eq(sprouts.harvest_name(-1), "Shifting Sprouts", "no variant falls back to the crop name")
	check_eq(game.crops["potato"].yield_count, 6, "potato bags yield six")
	check(game.crops["peas"].trellis, "peas climb a trellis")


func test_flowers_and_favourites() -> void:
	check_eq(game.crops["moonpetal"].kind, "flower", "moonpetal is a flower")
	check_eq(game.crops["blood_blossom"].kind, "crop", "blood blossom is a crop")
	check_eq(game.crops["sirens_bell"].favoured_by, "mermaid", "siren's bell is the mermaid flower")


func test_atlas_layout() -> void:
	var crop: CropData = CropData.from_dict("x", {"stage_days": [1, 1, 1], "sell_price": 5, "seasons": ["spring"]})
	crop.apply_layout({"row": 4, "stages": {"seed": 0, "sprout": 3}})
	check_eq(crop.atlas_row, 4, "row from layout")
	check_eq(crop.atlas_column(0), 0, "seed column")
	check_eq(crop.atlas_column(1), 3, "sprout column")
	check_eq(crop.atlas_column(3), 3, "missing later stages fall back to the last one")
	crop.apply_layout({"row": 4, "stages": {"seed": 0, "sprout": 1, "growing": 2, "ready": 5}, "ready_variants": [5, 6, 7, 8]})
	check_eq(crop.atlas_column(3, 2), 7, "mature crops show their variant's column")
	check_eq(crop.atlas_column(1, 2), 1, "variants only apply once mature")
	check_eq(crop.bag_column, -1, "no bag column until the layout names one")
	crop.apply_layout({"row": 4, "stages": {"seed": 0, "bag": 9}})
	check_eq(crop.bag_column, 9, "bag column from layout")


func test_seed_choice() -> void:
	game.selected_seed = "dragon_root"
	check_eq(game.seed_for("spring").id, "dragon_root", "the chosen seed is planted")
	check_eq(game.seed_for("winter").id, "moonpetal", "a seed out of season falls back to the first that grows")
	game.selected_seed = ""
	check_eq(game.seeds_for("spring").size(), 19, "nineteen spring seeds to choose from")
