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
	check_eq(game.seed_for("spring").id, "mandrake", "first spring crop in crops.json")
	check_eq(game.seed_for("summer").id, "tomato", "summer seed")
	check(game.seed_for("winter") == null, "nothing grows in winter without an unlock")
	game.unlocks.append("root_cellar")
	check_eq(game.seed_for("winter").id, "potato", "unlocked seasonless crop fills winter")
	check_eq(game.seed_for("spring").id, "mandrake", "seasonal crops keep priority")


func test_save_round_trip() -> void:
	var path: String = temp_path("save.json")
	game.day = 33
	game.money = 210
	game.unlocks.append("root_cellar")
	var plot: Plot = game.plot_at(Vector2i(5, 7))
	plot.apply(Plot.Action.TILL, game.crops["peas"])
	plot.apply(Plot.Action.PLANT, game.crops["peas"])
	plot.days_grown = 3
	game.save(path)
	game.new_game()
	check(game.has_save(path), "save file exists")
	check(game.load_game(path), "load succeeds")
	check_eq(game.day, 33, "day")
	check_eq(game.money, 210, "money")
	check_eq(game.unlocks, ["root_cellar"] as Array[String], "unlocks")
	check_eq(game.plots.size(), 1, "one plot")
	var loaded: Plot = game.plot_at(Vector2i(5, 7))
	check_eq(loaded.crop.id, "peas", "crop")
	check_eq(loaded.days_grown, 3, "growth")


func test_load_rejects_missing_or_broken_save() -> void:
	var path: String = temp_path("broken.json")
	check(not game.load_game(path), "missing file")
	var file: FileAccess = FileAccess.open(path, FileAccess.WRITE)
	file.store_string("[1, 2, 3]")
	file.close()
	game.money = 9
	check(not game.load_game(path), "non-object json")
	check_eq(game.money, 9, "state untouched on failure")
