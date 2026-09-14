extends SceneTree
## Renders the grass test strip once per preset in data/grass.json into previews/grass/<preset>.png.


func _initialize() -> void:
	_render()


func _render() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/grass.json"))
	var packed: PackedScene = load("res://scenes/world/world.tscn")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://previews/grass"))
	var presets: Dictionary = data["presets"]
	var game: Node = root.get_node_or_null("Game")
	for preset: String in presets:
		var dials: Dictionary = presets[preset]
		if game != null and dials.has("day"):
			var day: float = dials["day"]
			game.set("day", int(day))
		var world: Node = packed.instantiate()
		world.set("map_path", "res://data/maps/grass_strip.txt")
		world.set("grass_preset", preset)
		root.add_child(world)
		for i: int in 4:
			await process_frame
		var err: Error = root.get_texture().get_image().save_png("res://previews/grass/%s.png" % preset)
		print("wrote ", preset if err == OK else "nothing (error %d)" % err)
		world.queue_free()
		await process_frame
	quit(0)
