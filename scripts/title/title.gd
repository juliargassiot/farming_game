extends Control

const FARM_SCENE: String = "res://scenes/farm/farm.tscn"
const UPDATE_EXIT_CODE: int = 42

@onready var continue_button: Button = $Center/Box/Continue
@onready var new_game_button: Button = $Center/Box/NewGame
@onready var update_button: Button = $Center/Box/Update
@onready var quit_button: Button = $Center/Box/Quit


func _ready() -> void:
	continue_button.visible = Game.has_save()
	continue_button.pressed.connect(_on_continue)
	new_game_button.pressed.connect(_on_new_game)
	update_button.pressed.connect(func() -> void: get_tree().quit(UPDATE_EXIT_CODE))
	quit_button.pressed.connect(func() -> void: get_tree().quit())
	(continue_button if continue_button.visible else new_game_button).grab_focus()


func _on_continue() -> void:
	Game.load_game()
	get_tree().change_scene_to_file(FARM_SCENE)


func _on_new_game() -> void:
	Game.new_game()
	get_tree().change_scene_to_file(FARM_SCENE)
