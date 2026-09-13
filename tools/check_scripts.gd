extends SceneTree


func _initialize() -> void:
	var paths: PackedStringArray = OS.get_cmdline_user_args()
	var failures: int = 0
	for path: String in paths:
		var script: Script = load("res://" + path.trim_prefix("res://"))
		if script == null or not script.can_instantiate():
			failures += 1
	print("scripts checked: %d, failed: %d" % [paths.size(), failures])
	quit(1 if failures > 0 else 0)
