class_name Calendar
extends RefCounted

const DAYS_PER_SEASON: int = 28
const SEASONS: Array[String] = ["spring", "summer", "autumn", "winter"]


static func season_index(day: int) -> int:
	@warning_ignore("integer_division")
	return ((day - 1) / DAYS_PER_SEASON) % SEASONS.size()


static func season_key(day: int) -> String:
	return SEASONS[season_index(day)]


static func day_of_season(day: int) -> int:
	return (day - 1) % DAYS_PER_SEASON + 1


static func year(day: int) -> int:
	@warning_ignore("integer_division")
	return (day - 1) / (DAYS_PER_SEASON * SEASONS.size()) + 1


static func label(day: int) -> String:
	return "%s %d, Year %d" % [season_key(day).capitalize(), day_of_season(day), year(day)]
