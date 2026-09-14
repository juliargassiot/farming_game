class_name TestCase
extends RefCounted
## Base for tests/test_*.gd. Each test_ method runs on a fresh instance with `game` reset and the random seed fixed.

var game: GameState
var failures: Array[String] = []


func setup() -> void:
	pass


func teardown() -> void:
	pass


func fail(message: String) -> void:
	failures.append(message)


func check(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)


func check_eq(actual: Variant, expected: Variant, message: String) -> void:
	if actual != expected:
		failures.append("%s: expected %s, got %s" % [message, expected, actual])


func check_near(actual: float, expected: float, tolerance: float, message: String) -> void:
	if absf(actual - expected) > tolerance:
		failures.append("%s: expected %s within %s, got %s" % [message, expected, tolerance, actual])


func temp_path(name: String) -> String:
	return "user://tests/" + name
