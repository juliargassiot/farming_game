extends SceneTree


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty():
		printerr("usage: screenshot.sh scenes/<system>/<scene>.tscn")
		quit(2)
		return
	_capture(args[0])


func _capture(scene_path: String) -> void:
	var packed: PackedScene = load("res://" + scene_path.trim_prefix("res://"))
	if packed == null:
		printerr("cannot load ", scene_path)
		quit(1)
		return
	var game: Node = root.get_node_or_null("Game")
	if game != null and game.call("has_save"):
		game.call("load_game")
	root.add_child(packed.instantiate())
	for i: int in 4:
		await process_frame
	var out: String = "res://previews/" + scene_path.get_file().get_basename() + ".png"
	var err: Error = root.get_texture().get_image().save_png(out)
	print("wrote ", out if err == OK else "nothing (error %d)" % err)
	quit(0 if err == OK else 1)
