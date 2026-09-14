extends SceneTree


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty():
		printerr("usage: screenshot.sh scenes/<system>/<scene>.tscn [name] [x,y]")
		quit(2)
		return
	_capture(args[0], args[1] if args.size() > 1 else args[0].get_file().get_basename(), args[2] if args.size() > 2 else "")


func _capture(scene_path: String, name: String, at: String) -> void:
	var packed: PackedScene = load("res://" + scene_path.trim_prefix("res://"))
	if packed == null:
		printerr("cannot load ", scene_path)
		quit(1)
		return
	var game: Node = root.get_node_or_null("Game")
	if game != null and game.call("has_save"):
		game.call("load_game")
	var scene: Node = packed.instantiate()
	root.add_child(scene)
	await process_frame
	var player: Node = scene.find_child("Player")
	if at != "" and player != null:
		var parts: PackedStringArray = at.split(",")
		player.call("place_at_cell", Vector2i(int(parts[0]), int(parts[1])))
	if scene.has_method("open"):
		scene.call("open", "spring")
	for i: int in 4:
		await process_frame
	var out: String = "res://previews/" + name + ".png"
	var err: Error = root.get_texture().get_image().save_png(out)
	print("wrote ", out if err == OK else "nothing (error %d)" % err)
	quit(0 if err == OK else 1)
