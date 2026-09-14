class_name TerrainPainter
extends RefCounted
## Paints the soil Wang tiles on a dual grid: layer cell (i, j) sits half a tile up-left of map cell (i, j),
## and its tile is chosen by which of the four map cells around that point are marked.

const TILLED_ROW: int = 4
const WET_ROW: int = 8


static func paint(layer: TileMapLayer, marked: Dictionary[Vector2i, bool], first_row: int, bounds: Rect2i) -> void:
	"""Repaints the dual cells inside bounds; a cell with no marked corner is erased so the painted grass shows."""
	for j: int in range(bounds.position.y, bounds.end.y):
		for i: int in range(bounds.position.x, bounds.end.x):
			var index: int = 0
			for corner: Vector2i in [Vector2i(i - 1, j - 1), Vector2i(i, j - 1), Vector2i(i - 1, j), Vector2i(i, j)]:
				index = index * 2 + (1 if marked.has(corner) else 0)
			var cell: Vector2i = Vector2i(i, j)
			if index > 0:
				@warning_ignore("integer_division")
				layer.set_cell(cell, 0, Vector2i(index % 4, first_row + index / 4))
			else:
				layer.erase_cell(cell)
