extends TestCase

const TEXT: String = """
wwwww
,,,,,
.P.T.
#=#XX
.sBXd
"""
const DATA: Dictionary = {
	"regions": {
		"coast": {"name": "Coast", "race": "mermaid", "kind": "coast", "rect": [0, 0, 5, 2], "combat_zone": true},
		"farm": {"name": "Farm", "kind": "farm", "rect": [0, 2, 5, 5]},
	},
	"buildings": {"3,4": "farmhouse"},
	"exits": {"0,2": {"map": "peaks", "at": "6,54", "facing": "north"}},
}


func test_reads_symbols_and_landmarks() -> void:
	var map: WorldMap = WorldMap.from_text(TEXT, DATA)
	check_eq(map.size, Vector2i(5, 5), "size comes from the grid")
	check_eq(map.start, Vector2i(1, 2), "player start")
	check_eq(map.beds.keys(), [Vector2i(2, 4)], "bed cells")
	check(map.is_walkable(Vector2i(4, 4)), "doors are walkable")
	var peaks: WorldMap = WorldMap.from_text("r-^")
	check(peaks.is_walkable(Vector2i(0, 0)) and peaks.is_walkable(Vector2i(1, 0)), "ledges and trails are walkable")
	check(not peaks.is_walkable(Vector2i(2, 0)), "cliffs block")
	check(not map.is_walkable(Vector2i(3, 3)), "building footprints block")
	check_eq(map.farmable.keys(), [Vector2i(1, 4)], "field cells")
	check_eq(map.ground_at(Vector2i(0, 0)), WorldMap.Ground.SEA, "sea")
	var exit: WorldMap.Exit = map.exits[Vector2i(0, 2)]
	check(exit.map_name == "peaks" and exit.at == Vector2i(6, 54) and exit.facing == Vector2i(0, -1), "exit leads to the far map")
	check_eq(map.ground_at(Vector2i(3, 2)), WorldMap.Ground.TREE, "tree")
	check_eq(map.ground_at(Vector2i(1, 2)), WorldMap.Ground.GRASS, "the start stands on grass")
	check_eq(map.ground_at(Vector2i(9, 9)), WorldMap.Ground.GRASS, "outside the map reads as grass")


func test_walkable_and_bounds() -> void:
	var map: WorldMap = WorldMap.from_text(TEXT)
	check(map.is_walkable(Vector2i(1, 1)), "sand is walkable")
	check(map.is_walkable(Vector2i(1, 3)), "path is walkable")
	check(not map.is_walkable(Vector2i(0, 0)), "sea is solid")
	check(not map.is_walkable(Vector2i(3, 3)), "footprint is solid")
	check(not map.is_walkable(Vector2i(-1, 2)), "off the left edge")
	check(not map.is_walkable(Vector2i(2, 5)), "off the bottom edge")
	check_eq(map.farm_bounds(), Rect2i(1, 4, 2, 2), "farm bounds cover the dual cells around the field")


func test_regions() -> void:
	var map: WorldMap = WorldMap.from_text(TEXT, DATA)
	check_eq(map.regions.size(), 2, "two regions")
	check_eq(map.buildings, {Vector2i(3, 4): "farmhouse"}, "buildings anchor at the cell the data names")
	var coast: WorldMap.Region = map.region_at(Vector2i(4, 1))
	check(coast != null and coast.id == "coast" and coast.race == "mermaid" and coast.combat_zone, "coast region fields")
	var farm: WorldMap.Region = map.region_at(Vector2i(2, 4))
	check(farm != null and farm.display_name == "Farm" and not farm.combat_zone, "farm region defaults")
	check(WorldMap.from_text(TEXT).region_at(Vector2i(2, 4)) == null, "no regions without data")


func test_reachable_stops_at_solid_cells() -> void:
	var map: WorldMap = WorldMap.from_text(TEXT)
	var seen: Dictionary[Vector2i, bool] = map.reachable_from(map.start)
	check(seen.has(Vector2i(4, 2)), "walks past the tree to the top right")
	check(not seen.has(Vector2i(4, 4)), "the door behind the footprint is cut off")
	check(seen.has(Vector2i(0, 1)), "reaches the beach")
	check(not seen.has(Vector2i(0, 0)), "never enters the sea")
	check(not seen.has(Vector2i(2, 4)), "the bed blocks")
	check_eq(seen.size(), 12, "every open cell is counted once")
