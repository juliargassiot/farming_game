extends SceneTree
## Drops the farmer on the hub's north gate, lets the crossing play out, and screenshots where they land.


func _initialize() -> void:
	var packed: PackedScene = load("res://scenes/world/world.tscn")
	var scene: Node = packed.instantiate()
	root.add_child(scene)
	await process_frame
	var player: Node = scene.find_child("Player")
	player.call("place_at_cell", Vector2i(60, 0))
	await create_timer(2.5).timeout
	var err: Error = root.get_texture().get_image().save_png("res://previews/crossing-check.png")
	print("landed on ", scene.get("map_path"), " region ", scene.get_node("HUD/Region").get("text"), " err ", err)
	quit(0)
