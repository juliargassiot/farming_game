extends SceneTree

var failures: Array[String] = []
var passed: int = 0


func _initialize() -> void:
	for path: String in _test_scripts():
		var script: GDScript = load(path)
		if script == null or not script.can_instantiate():
			failures.append(path + ": does not compile")
			continue
		var case: TestCase = script.new()
		case.game = root.get_node("Game")
		for method: Dictionary in case.get_method_list():
			var name: String = method["name"]
			if not name.begins_with("test_"):
				continue
			case.failures.clear()
			case.call(name)
			if case.failures.is_empty():
				passed += 1
			else:
				for message: String in case.failures:
					failures.append("%s.%s: %s" % [path.get_file(), name, message])
	for failure: String in failures:
		printerr("FAIL ", failure)
	print("tests: %d passed, %d failed" % [passed, failures.size()])
	quit(1 if failures.size() > 0 else 0)


func _test_scripts() -> Array[String]:
	var found: Array[String] = []
	var dir: DirAccess = DirAccess.open("res://tests")
	if dir != null:
		for name: String in dir.get_files():
			if name.begins_with("test_") and name.ends_with(".gd"):
				found.append("res://tests/" + name)
	found.sort()
	return found
