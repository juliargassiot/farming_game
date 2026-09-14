class_name TerrainPainter
extends RefCounted
## Paints the seasonal Wang tiles on a dual grid: layer cell (i, j) sits half a tile up-left of map cell (i, j),
## and its tile is chosen by which of the four map cells around that point are marked.

const VARIANT_ROW: int = 4
const VARIANT_KINDS: int = 6
const TILLED_ROW: int = 7
const WET_ROW: int = 11


static func paint(layer: TileMapLayer, marked: Dictionary[Vector2i, bool], first_row: int, bounds: Rect2i, fill_open: bool) -> Array[Vector2i]:
	"""Repaints the dual cells inside bounds. With fill_open, unmarked cells get the flat tile and are returned."""
	var open: Array[Vector2i] = []
	for j: int in range(bounds.position.y, bounds.end.y):
		for i: int in range(bounds.position.x, bounds.end.x):
			var index: int = 0
			for corner: Vector2i in [Vector2i(i - 1, j - 1), Vector2i(i, j - 1), Vector2i(i - 1, j), Vector2i(i, j)]:
				index = index * 2 + (1 if marked.has(corner) else 0)
			var cell: Vector2i = Vector2i(i, j)
			if index > 0:
				@warning_ignore("integer_division")
				layer.set_cell(cell, 0, Vector2i(index % 4, first_row + index / 4))
			elif fill_open:
				layer.set_cell(cell, 0, Vector2i.ZERO)
				open.append(cell)
			else:
				layer.erase_cell(cell)
	return open


static func variant_coords(cell: Vector2i, kind: int) -> Vector2i:
	var index: int = hash(cell * 3) % VARIANT_KINDS + (VARIANT_KINDS if kind == Grass.BLADES else 0)
	@warning_ignore("integer_division")
	return Vector2i(index % 4, VARIANT_ROW + index / 4)


static func is_textured(atlas_coords: Vector2i) -> bool:
	return atlas_coords.y >= VARIANT_ROW and atlas_coords.y < TILLED_ROW
