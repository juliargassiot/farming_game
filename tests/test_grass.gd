extends TestCase

var cells: Array[Vector2i] = []


func setup() -> void:
	for y: int in 20:
		for x: int in 20:
			cells.append(Vector2i(x, y))


func test_coverage_is_exact() -> void:
	var grass: Grass = Grass.new()
	grass.coverage = 0.25
	grass.flowers = 0.0
	var assigned: Dictionary[Vector2i, int] = grass.assign(cells)
	check_eq(assigned.size(), cells.size(), "every cell is assigned")
	check_eq(_count(assigned, Grass.BLADES), 100, "a quarter of 400 cells carry texture")
	check_eq(_count(assigned, Grass.FLOWERS), 0, "no flowers at zero")


func test_flowers_split_textured_cells() -> void:
	var grass: Grass = Grass.new()
	grass.coverage = 0.5
	grass.flowers = 0.5
	var assigned: Dictionary[Vector2i, int] = grass.assign(cells)
	check_eq(_count(assigned, Grass.FLOWERS), 100, "half the textured cells keep flowers")
	check_eq(_count(assigned, Grass.BLADES), 100, "the rest are blades")


func test_assignment_is_deterministic() -> void:
	var grass: Grass = Grass.new()
	check_eq(grass.assign(cells), grass.assign(cells), "same dials give the same map")
	var scattered: Grass = Grass.new()
	scattered.clumpiness = 0.0
	check(scattered.assign(cells) != grass.assign(cells), "clumpiness changes the layout")


func test_edge_cases() -> void:
	var grass: Grass = Grass.new()
	check(grass.assign([] as Array[Vector2i]).is_empty(), "no cells")
	grass.coverage = 0.0
	check_eq(_count(grass.assign(cells), Grass.PLAIN), 400, "zero coverage leaves everything plain")
	grass.coverage = 1.0
	check_eq(_count(grass.assign(cells), Grass.PLAIN), 0, "full coverage textures everything")


func test_load_dials() -> void:
	var spring: Grass = Grass.load_dials("spring")
	check(spring.coverage > 0.0 and spring.coverage <= 1.0, "season dials load")
	var preset: Grass = Grass.load_dials("spring", "Winter")
	check_eq(preset.coverage, Grass.load_dials("winter").coverage, "preset wins over season")
	check_eq(Grass.load_dials("summer", "no such preset").coverage, Grass.load_dials("summer").coverage, "unknown preset falls back")


func _count(assigned: Dictionary[Vector2i, int], kind: int) -> int:
	var n: int = 0
	for cell: Vector2i in assigned:
		if assigned[cell] == kind:
			n += 1
	return n
