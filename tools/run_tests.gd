extends SceneTree
## Runs every test_ method in tests/test_*.gd. Optional user args filter by substring of "file.method".

const SEED: int = 20260914
const TEMP_DIR: String = "user://tests"

var failures: Array[String] = []
var passed: int = 0


func _initialize() -> void:
	var filters: PackedStringArray = OS.get_cmdline_user_args()
	var game: GameState = root.get_node("Game")
	for path: String in _test_scripts():
		var script: GDScript = load(path)
		if script == null or not script.can_instantiate():
			failures.append(path.get_file() + ": does not compile")
			continue
		for name: String in _test_methods(script):
			var label: String = "%s.%s" % [path.get_file(), name]
			if not _selected(label, filters):
				continue
			_run_one(script, name, label, game)
	for failure: String in failures:
		printerr("FAIL ", failure)
	print("tests: %d passed, %d failed" % [passed, failures.size()])
	quit(1 if failures.size() > 0 or passed == 0 else 0)


func _run_one(script: GDScript, name: String, label: String, game: GameState) -> void:
	_reset_temp_dir()
	game.new_game()
	seed(SEED)
	var case: TestCase = script.new()
	case.game = game
	case.setup()
	case.call(name)
	case.teardown()
	game.new_game()
	if case.failures.is_empty():
		passed += 1
	for message: String in case.failures:
		failures.append("%s: %s" % [label, message])


func _selected(label: String, filters: PackedStringArray) -> bool:
	if filters.is_empty():
		return true
	for filter: String in filters:
		if label.contains(filter):
			return true
	return false


func _test_methods(script: GDScript) -> Array[String]:
	var names: Array[String] = []
	for method: Dictionary in script.get_script_method_list():
		var name: String = method["name"]
		if name.begins_with("test_") and not names.has(name):
			names.append(name)
	return names


func _test_scripts() -> Array[String]:
	var found: Array[String] = []
	var dir: DirAccess = DirAccess.open("res://tests")
	if dir != null:
		for name: String in dir.get_files():
			if name.begins_with("test_") and name.ends_with(".gd") and name != "test_case.gd":
				found.append("res://tests/" + name)
	found.sort()
	return found


func _reset_temp_dir() -> void:
	var dir: DirAccess = DirAccess.open("user://")
	if dir.dir_exists(TEMP_DIR):
		for name: String in DirAccess.get_files_at(TEMP_DIR):
			dir.remove(TEMP_DIR + "/" + name)
	else:
		dir.make_dir_recursive(TEMP_DIR)
