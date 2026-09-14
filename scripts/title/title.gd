extends Control

const WORLD_SCENE: String = "res://scenes/world/world.tscn"
const UPDATE_EXIT_CODE: int = 42

@onready var continue_button: Button = $Center/Box/Continue
@onready var new_game_button: Button = $Center/Box/NewGame
@onready var update_button: Button = $Center/Box/Update
@onready var quit_button: Button = $Center/Box/Quit
@onready var controller_label: Label = $Controller


func _ready() -> void:
	continue_button.visible = Game.has_save()
	continue_button.pressed.connect(_on_continue)
	new_game_button.pressed.connect(_on_new_game)
	update_button.pressed.connect(func() -> void: get_tree().quit(UPDATE_EXIT_CODE))
	quit_button.pressed.connect(func() -> void: get_tree().quit())
	_focus_default()
	Input.joy_connection_changed.connect(func(_device: int, _connected: bool) -> void: _refresh_controller_label())
	_refresh_controller_label()


## Fallback for layouts that only emit the game's own actions (WASD/E, or a joypad Godot maps
## outside the built-in ui_* actions). Events the focused button already consumed never reach here.
func _unhandled_input(event: InputEvent) -> void:
	var focused: Control = get_viewport().gui_get_focus_owner()
	if focused == null:
		if event.is_action_pressed("move_up") or event.is_action_pressed("move_down") or event.is_action_pressed("interact"):
			_focus_default()
			get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("move_down"):
		_move_focus(focused, true)
	elif event.is_action_pressed("move_up"):
		_move_focus(focused, false)
	elif event.is_action_pressed("interact") and focused is Button:
		(focused as Button).pressed.emit()
	else:
		return
	get_viewport().set_input_as_handled()


func _focus_default() -> void:
	(continue_button if continue_button.visible else new_game_button).grab_focus()


func _move_focus(from: Control, forward: bool) -> void:
	var next: Control = from.find_next_valid_focus() if forward else from.find_prev_valid_focus()
	if next != null:
		next.grab_focus()


func _refresh_controller_label() -> void:
	var names: PackedStringArray = PackedStringArray()
	for device: int in Input.get_connected_joypads():
		names.append(Input.get_joy_name(device))
	if names.is_empty():
		controller_label.text = "No controller detected. Keyboard: arrows or WASD, Enter or Space."
	else:
		controller_label.text = "Controller: " + ", ".join(names)


func _on_continue() -> void:
	Game.load_game()
	get_tree().change_scene_to_file(WORLD_SCENE)


func _on_new_game() -> void:
	Game.new_game()
	get_tree().change_scene_to_file(WORLD_SCENE)
