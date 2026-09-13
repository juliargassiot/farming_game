class_name Player
extends CharacterBody2D

signal interact(cell: Vector2i)

const SPEED: float = 160.0
const TILE: int = 32
const DIRECTION_NAMES: Dictionary[Vector2i, String] = {
	Vector2i(0, 1): "south", Vector2i(0, -1): "north", Vector2i(1, 0): "east", Vector2i(-1, 0): "west",
}

var facing: Vector2i = Vector2i(0, 1)

@onready var sprite: AnimatedSprite2D = $Sprite


func _physics_process(_delta: float) -> void:
	var input: Vector2 = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	velocity = input * SPEED
	move_and_slide()
	if input.length() > 0.1:
		facing = Vector2i(int(signf(input.x)), 0) if absf(input.x) >= absf(input.y) else Vector2i(0, int(signf(input.y)))
		sprite.play("walk_" + DIRECTION_NAMES[facing])
	else:
		sprite.play("idle_" + DIRECTION_NAMES[facing])
	if Input.is_action_just_pressed("interact"):
		interact.emit(target_cell())


func target_cell() -> Vector2i:
	var probe: Vector2 = position + Vector2(facing) * 20.0
	return Vector2i(floori(probe.x / TILE), floori(probe.y / TILE))


func place_at_cell(cell: Vector2i) -> void:
	position = Vector2(cell) * TILE + Vector2(TILE / 2.0, TILE / 2.0)
