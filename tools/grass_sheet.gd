extends SceneTree
## Renders the grass test strip once per preset in data/grass.json into previews/grass/<preset>.png.


func _initialize() -> void:
	_render()


func _render() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/grass.json"))
	var packed: PackedScene = load("res://scenes/farm/farm.tscn")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://previews/grass"))
	for preset: String in data["presets"]:
		var farm: Node = packed.instantiate()
		farm.set("map_path", "res://data/maps/grass_strip.txt")
		farm.set("grass_preset", preset)
		root.add_child(farm)
		for i: int in 4:
			await process_frame
		var err: Error = root.get_texture().get_image().save_png("res://previews/grass/%s.png" % preset)
		print("wrote ", preset if err == OK else "nothing (error %d)" % err)
		farm.queue_free()
		await process_frame
	quit(0)
