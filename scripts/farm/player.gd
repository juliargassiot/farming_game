class_name Player
extends CharacterBody2D

signal interact(cell: Vector2i)
signal entered_cell(cell: Vector2i, direction: Vector2i)

const SPEED: float = 160.0
const TILE: int = 32
const DIRECTION_NAMES: Dictionary[Vector2i, String] = {
	Vector2i(0, 1): "south", Vector2i(0, -1): "north", Vector2i(1, 0): "east", Vector2i(-1, 0): "west",
}
const DIRECTIONS: Dictionary[String, Vector2i] = {
	"south": Vector2i(0, 1), "north": Vector2i(0, -1), "east": Vector2i(1, 0), "west": Vector2i(-1, 0),
}

var facing: Vector2i = Vector2i(0, 1)
var cell: Vector2i = Vector2i(-1, -1)
var bounds: Rect2 = Rect2()

@onready var sprite: AnimatedSprite2D = $Sprite


func _physics_process(_delta: float) -> void:
	var input: Vector2 = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	velocity = input * SPEED
	move_and_slide()
	if bounds.size != Vector2.ZERO:
		position = position.clamp(bounds.position, bounds.end)
	var now: Vector2i = Vector2i(floori(position.x / TILE), floori(position.y / TILE))
	if now != cell:
		cell = now
		entered_cell.emit(now, facing)
	var moving: bool = input.length() > 0.1
	if moving:
		facing = Vector2i(int(signf(input.x)), 0) if absf(input.x) >= absf(input.y) else Vector2i(0, int(signf(input.y)))
		sprite.play("walk_" + DIRECTION_NAMES[facing])
	else:
		sprite.play("stand_" + DIRECTION_NAMES[facing])
	if Input.is_action_just_pressed("interact"):
		interact.emit(target_cell())


func target_cell() -> Vector2i:
	var probe: Vector2 = position + Vector2(facing) * 20.0
	return Vector2i(floori(probe.x / TILE), floori(probe.y / TILE))


func place_at_cell(at: Vector2i, face: Vector2i = facing) -> void:
	position = Vector2(at) * TILE + Vector2(TILE / 2.0, TILE / 2.0)
	facing = face
