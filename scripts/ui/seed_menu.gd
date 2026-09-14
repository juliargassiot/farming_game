class_name SeedMenu
extends PanelContainer
## Placeholder seed picker: this season's seeds with their seed bag as icon. The rucksack replaces it later.

signal closed

const CROP_ATLAS: Texture2D = preload("res://assets/tiles/crops.png")

@onready var list: ItemList = $Box/List


func open(season: String) -> void:
	list.clear()
	var options: Array[CropData] = Game.seeds_for(season)
	for crop: CropData in options:
		var icon: AtlasTexture = AtlasTexture.new()
		icon.atlas = CROP_ATLAS
		var column: int = crop.bag_column if crop.bag_column >= 0 else crop.atlas_column(1)
		icon.region = Rect2(column * 32, crop.atlas_row * 32, 32, 32)
		list.add_item(crop.display_name, icon)
		list.set_item_metadata(list.item_count - 1, crop.id)
		if crop.id == Game.selected_seed:
			list.select(list.item_count - 1)
	if list.item_count > 0 and list.get_selected_items().is_empty():
		list.select(0)
	visible = true
	list.grab_focus()
	if not list.get_selected_items().is_empty():
		list.ensure_current_is_visible()


func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	var selected: PackedInt32Array = list.get_selected_items()
	var index: int = selected[0] if not selected.is_empty() else 0
	if event.is_action_pressed("move_down"):
		list.select(mini(index + 1, list.item_count - 1))
	elif event.is_action_pressed("move_up"):
		list.select(maxi(index - 1, 0))
	elif event.is_action_pressed("interact"):
		Game.selected_seed = list.get_item_metadata(index)
		_close()
	elif event.is_action_pressed("cancel") or event.is_action_pressed("seed_menu"):
		_close()
	else:
		return
	list.ensure_current_is_visible()
	get_viewport().set_input_as_handled()


func _close() -> void:
	visible = false
	closed.emit()
