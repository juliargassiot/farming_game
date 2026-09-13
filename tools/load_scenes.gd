extends SceneTree


func _initialize() -> void:
	var failures: int = 0
	for path: String in _scene_paths("res://scenes"):
		var packed: PackedScene = load(path)
		var instance: Node = packed.instantiate() if packed != null else null
		if instance == null:
			printerr("cannot instantiate ", path)
			failures += 1
		else:
			instance.free()
	print("scenes loaded: ", failures, " failures")
	quit(1 if failures > 0 else 0)


func _scene_paths(dir_path: String) -> Array[String]:
	var found: Array[String] = []
	var dir: DirAccess = DirAccess.open(dir_path)
	if dir == null:
		return found
	for name: String in dir.get_directories():
		found.append_array(_scene_paths(dir_path + "/" + name))
	for name: String in dir.get_files():
		if name.ends_with(".tscn"):
			found.append(dir_path + "/" + name)
	return found
