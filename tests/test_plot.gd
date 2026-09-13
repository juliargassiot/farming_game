extends TestCase

var turnip: CropData = CropData.from_dict("turnip", {"stage_days": [1, 1, 1], "sell_price": 30, "seasons": ["spring"]})
var potato: CropData = CropData.from_dict("potato", {"stage_days": [2, 2, 2], "sell_price": 60, "seasons": ["spring"]})


func test_till_plant_water_harvest() -> void:
	var plot: Plot = Plot.new()
	check_eq(plot.next_action(turnip), Plot.Action.TILL, "fresh plot needs tilling")
	plot.apply(Plot.Action.TILL, turnip)
	check_eq(plot.next_action(turnip), Plot.Action.PLANT, "tilled plot takes seeds")
	check_eq(plot.next_action(null), Plot.Action.NONE, "no seed means nothing to do")
	plot.apply(Plot.Action.PLANT, turnip)
	check_eq(plot.next_action(turnip), Plot.Action.WATER, "planted plot wants water")
	plot.apply(Plot.Action.WATER, turnip)
	check_eq(plot.next_action(turnip), Plot.Action.NONE, "watered plot waits")
	for day: int in 3:
		plot.advance_day()
		plot.apply(Plot.Action.WATER, turnip)
	check_eq(plot.next_action(turnip), Plot.Action.HARVEST, "mature crop harvests")
	check_eq(plot.apply(Plot.Action.HARVEST, turnip), 30, "harvest pays the sell price")
	check(plot.crop == null and plot.tilled, "harvest clears the crop and keeps the soil tilled")


func test_unwatered_crops_do_not_grow() -> void:
	var plot: Plot = Plot.new()
	plot.apply(Plot.Action.TILL, turnip)
	plot.apply(Plot.Action.PLANT, turnip)
	plot.advance_day()
	check_eq(plot.days_grown, 0, "dry crop stays put")


func test_round_trip() -> void:
	var plot: Plot = Plot.new()
	plot.apply(Plot.Action.TILL, potato)
	plot.apply(Plot.Action.PLANT, potato)
	plot.days_grown = 4
	var copy: Plot = Plot.from_dict(plot.to_dict(), {"potato": potato})
	check_eq(copy.crop.id, "potato", "crop survives save")
	check_eq(copy.days_grown, 4, "growth survives save")
	check(copy.tilled, "tilled survives save")
