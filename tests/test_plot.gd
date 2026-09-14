extends TestCase

var turnip: CropData = CropData.from_dict("turnip", {"stage_days": [1, 1, 1], "sell_price": 30, "seasons": ["spring"]})
var berry: CropData = CropData.from_dict("berry", {"stage_days": [1, 1, 2], "sell_price": 10, "seasons": ["spring"], "regrow_days": 1, "yield": 3,
	"variants": ["Red", "Blue"]})
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


func test_regrow_yield_and_variant() -> void:
	var plot: Plot = Plot.new()
	plot.apply(Plot.Action.TILL, berry)
	plot.apply(Plot.Action.PLANT, berry)
	check(plot.variant == 0 or plot.variant == 1, "a hidden variant is chosen at planting")
	plot.days_grown = 4
	check_eq(plot.apply(Plot.Action.HARVEST, berry), 30, "harvest pays price times yield")
	check(plot.crop == berry, "regrowing crop stays planted")
	check_eq(plot.days_grown, 3, "regrowth resumes one regrow period before maturity")
	var copy: Plot = Plot.from_dict(plot.to_dict(), {"berry": berry})
	check_eq(copy.variant, plot.variant, "variant survives save")


func test_grow_one_stage() -> void:
	var plot: Plot = Plot.new()
	plot.apply(Plot.Action.TILL, potato)
	plot.apply(Plot.Action.PLANT, potato)
	plot.grow_one_stage()
	check_eq(plot.days_grown, 2, "first press reaches the second stage")
	plot.grow_one_stage()
	plot.grow_one_stage()
	check(plot.crop.is_mature(plot.days_grown), "three presses ripen a three-stage crop")
	plot.grow_one_stage()
	check_eq(plot.days_grown, 6, "mature crops stop")
