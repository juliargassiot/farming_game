extends TestCase

var layer: TileMapLayer


func setup() -> void:
	layer = TileMapLayer.new()


func teardown() -> void:
	layer.free()


func test_single_marked_cell_paints_its_four_corners() -> void:
	var marked: Dictionary[Vector2i, bool] = {Vector2i(1, 1): true}
	TerrainPainter.paint(layer, marked, 0, Rect2i(0, 0, 4, 4))
	check_eq(layer.get_used_cells().size(), 4, "four dual cells touch the marked cell")
	check_eq(layer.get_cell_atlas_coords(Vector2i(1, 1)), Vector2i(1, 0), "only the SE corner marked is mask 1")
	check_eq(layer.get_cell_atlas_coords(Vector2i(2, 2)), Vector2i(0, 2), "only the NW corner marked is mask 8")


func test_unmarked_cells_stay_empty() -> void:
	TerrainPainter.paint(layer, {}, 0, Rect2i(0, 0, 3, 2))
	check_eq(layer.get_used_cells().size(), 0, "nothing marked paints nothing")


func test_repaint_erases_unmarked_cells() -> void:
	var marked: Dictionary[Vector2i, bool] = {Vector2i(1, 1): true}
	TerrainPainter.paint(layer, marked, TerrainPainter.TILLED_ROW, Rect2i(0, 0, 4, 4))
	check_eq(layer.get_cell_atlas_coords(Vector2i(1, 1)), Vector2i(1, TerrainPainter.TILLED_ROW), "tilled rows start at the block's first row")
	TerrainPainter.paint(layer, {}, TerrainPainter.TILLED_ROW, Rect2i(0, 0, 4, 4))
	check_eq(layer.get_used_cells().size(), 0, "cleared once nothing is marked")
