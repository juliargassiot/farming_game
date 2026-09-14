extends TestCase

var player: Player


func setup() -> void:
	player = Player.new()


func teardown() -> void:
	player.free()


func test_place_at_cell_centers_the_farmer() -> void:
	player.place_at_cell(Vector2i(3, 5))
	check_eq(player.position, Vector2(112, 176), "tile center")


func test_target_cell_follows_facing() -> void:
	player.place_at_cell(Vector2i(3, 5))
	check_eq(player.target_cell(), Vector2i(3, 6), "faces south by default")
	player.facing = Vector2i(-1, 0)
	check_eq(player.target_cell(), Vector2i(2, 5), "west")
	player.facing = Vector2i(0, -1)
	check_eq(player.target_cell(), Vector2i(3, 4), "north")
