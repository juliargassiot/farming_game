extends TestCase


func test_new_game_resets_everything() -> void:
	game.day = 40
	game.money = 500
	game.plot_at(Vector2i(1, 1)).tilled = true
	game.unlocks.append("root_cellar")
	game.new_game()
	check_eq(game.day, 1, "day")
	check_eq(game.money, 0, "money")
	check(game.plots.is_empty(), "plots")
	check(game.unlocks.is_empty(), "unlocks")


func test_plot_at_creates_once() -> void:
	var plot: Plot = game.plot_at(Vector2i(3, 4))
	check(plot == game.plot_at(Vector2i(3, 4)), "same cell returns the same plot")
	check(plot != game.plot_at(Vector2i(4, 3)), "another cell gets its own plot")
	check_eq(game.plots.size(), 2, "only touched cells exist")


func test_advance_day_grows_every_watered_plot() -> void:
	var crop: CropData = game.crops["carrot"]
	var wet: Plot = game.plot_at(Vector2i(0, 0))
	var dry: Plot = game.plot_at(Vector2i(1, 0))
	for plot: Plot in [wet, dry]:
		plot.apply(Plot.Action.TILL, crop)
		plot.apply(Plot.Action.PLANT, crop)
	wet.apply(Plot.Action.WATER, crop)
	game.advance_day()
	check_eq(game.day, 2, "day advances")
	check_eq(wet.days_grown, 1, "watered plot grows")
	check_eq(dry.days_grown, 0, "dry plot waits")
	check(not wet.watered, "water dries overnight")


func test_seed_for_season_respects_unlocks() -> void:
	var roster: Dictionary[String, CropData] = game.crops
	game.crops = {
		"cellar_bulb": CropData.from_dict("cellar_bulb", {"stage_days": [1], "sell_price": 1, "requires": "root_cellar"}),
		"turnip": CropData.from_dict("turnip", {"stage_days": [1], "sell_price": 1, "seasons": ["spring"]}),
	}
	check_eq(game.seed_for("spring").id, "turnip", "first crop that grows in the season")
	check(game.seed_for("winter") == null, "locked seasonless crop stays hidden")
	game.unlocks.append("root_cellar")
	check_eq(game.seed_for("winter").id, "cellar_bulb", "unlocked seasonless crop fills any season")
	check_eq(game.seed_for("spring").id, "cellar_bulb", "roster order decides between two candidates")
	game.crops = roster


func test_save_round_trip() -> void:
	var path: String = temp_path("save.json")
	game.day = 33
	game.money = 210
	game.unlocks.append("root_cellar")
	var plot: Plot = game.plot_at(Vector2i(5, 7))
	plot.apply(Plot.Action.TILL, game.crops["peas"])
	plot.apply(Plot.Action.PLANT, game.crops["peas"])
	plot.days_grown = 3
	var exit: WorldMap.Exit = WorldMap.Exit.from_dict({"map": "fangridge", "at": "6,54", "facing": "north"})
	game.travel(exit)
	game.save(path)
	game.new_game()
	check_eq(game.map_name, "world", "a new game starts on the overworld")
	check(game.has_save(path), "save file exists")
	check(game.load_game(path), "load succeeds")
	check_eq(game.day, 33, "day")
	check_eq(game.money, 210, "money")
	check_eq(game.unlocks, ["root_cellar"] as Array[String], "unlocks")
	check_eq(game.plots.size(), 1, "one plot")
	var loaded: Plot = game.plot_at(Vector2i(5, 7))
	check_eq(loaded.crop.id, "peas", "crop")
	check_eq(loaded.days_grown, 3, "growth")
	check(game.map_name == "fangridge" and game.cell == Vector2i(6, 54) and game.facing == Vector2i(0, -1), "where the farmer stood")
	check(not game.arriving, "loading a save is not a journey")


func test_load_rejects_missing_or_broken_save() -> void:
	var path: String = temp_path("broken.json")
	check(not game.load_game(path), "missing file")
	var file: FileAccess = FileAccess.open(path, FileAccess.WRITE)
	file.store_string("[1, 2, 3]")
	file.close()
	game.money = 9
	check(not game.load_game(path), "non-object json")
	check_eq(game.money, 9, "state untouched on failure")
