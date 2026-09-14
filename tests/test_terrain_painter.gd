extends TestCase

var layer: TileMapLayer


func setup() -> void:
	layer = TileMapLayer.new()


func teardown() -> void:
	layer.free()


func test_single_marked_cell_paints_its_four_corners() -> void:
	var marked: Dictionary[Vector2i, bool] = {Vector2i(1, 1): true}
	var open: Array[Vector2i] = TerrainPainter.paint(layer, marked, 0, Rect2i(0, 0, 4, 4), false)
	check(open.is_empty(), "nothing returned without fill")
	check_eq(layer.get_used_cells().size(), 4, "four dual cells touch the marked cell")
	check_eq(layer.get_cell_atlas_coords(Vector2i(1, 1)), Vector2i(1, 0), "only the SE corner marked is mask 1")
	check_eq(layer.get_cell_atlas_coords(Vector2i(2, 2)), Vector2i(0, 2), "only the NW corner marked is mask 8")


func test_fill_open_returns_flat_cells() -> void:
	var marked: Dictionary[Vector2i, bool] = {}
	var open: Array[Vector2i] = TerrainPainter.paint(layer, marked, 0, Rect2i(0, 0, 3, 2), true)
	check_eq(open.size(), 6, "every dual cell is open")
	check_eq(layer.get_cell_atlas_coords(Vector2i(2, 1)), Vector2i.ZERO, "open cells get the flat tile")


func test_repaint_erases_unmarked_cells() -> void:
	var marked: Dictionary[Vector2i, bool] = {Vector2i(1, 1): true}
	TerrainPainter.paint(layer, marked, TerrainPainter.TILLED_ROW, Rect2i(0, 0, 4, 4), false)
	TerrainPainter.paint(layer, {}, TerrainPainter.TILLED_ROW, Rect2i(0, 0, 4, 4), false)
	check_eq(layer.get_used_cells().size(), 0, "cleared once nothing is marked")


func test_variant_coords_stay_in_the_variant_rows() -> void:
	for x: int in 30:
		var coords: Vector2i = TerrainPainter.variant_coords(Vector2i(x, x * 7), Grass.FLOWERS)
		check(TerrainPainter.is_textured(coords), "flowered variant at %d is textured" % x)
		var blades: Vector2i = TerrainPainter.variant_coords(Vector2i(x, x * 7), Grass.BLADES)
		check(TerrainPainter.is_textured(blades) and blades != coords, "blade variant differs and is textured")
	check(not TerrainPainter.is_textured(Vector2i.ZERO), "flat tile is not textured")
	check(not TerrainPainter.is_textured(Vector2i(0, TerrainPainter.TILLED_ROW)), "tilled rows are not grass")
