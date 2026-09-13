extends TestCase


func test_first_day() -> void:
	check_eq(Calendar.season_key(1), "spring", "day 1 season")
	check_eq(Calendar.day_of_season(1), 1, "day 1 of season")
	check_eq(Calendar.year(1), 1, "day 1 year")


func test_season_boundaries() -> void:
	check_eq(Calendar.season_key(28), "spring", "last spring day")
	check_eq(Calendar.season_key(29), "summer", "first summer day")
	check_eq(Calendar.day_of_season(29), 1, "summer starts at 1")
	check_eq(Calendar.season_key(112), "winter", "last winter day")
	check_eq(Calendar.season_key(113), "spring", "year wraps")
	check_eq(Calendar.year(113), 2, "second year")


func test_label() -> void:
	check_eq(Calendar.label(30), "Summer 2, Year 1", "label format")
