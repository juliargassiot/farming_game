class_name GrassSway
extends Node2D
## A textured grass tile that bends away from the farmer for a moment, drawn over a flat copy of itself.

const LIFETIME: float = 0.7
const SHADER: Shader = preload("res://assets/shaders/grass_sway.gdshader")

var elapsed: float = 0.0
var material_instance: ShaderMaterial


static func spawn(parent: Node, tile_set: TileSet, plain: Vector2i, textured: Vector2i, at: Vector2, direction: float) -> GrassSway:
	var source: TileSetAtlasSource = tile_set.get_source(0)
	var sway: GrassSway = GrassSway.new()
	sway.position = at
	sway.add_child(sway._sprite(source, plain, null))
	sway.material_instance = ShaderMaterial.new()
	sway.material_instance.shader = SHADER
	sway.material_instance.set_shader_parameter("direction", direction)
	sway.add_child(sway._sprite(source, textured, sway.material_instance))
	parent.add_child(sway)
	return sway


func _sprite(source: TileSetAtlasSource, coords: Vector2i, shader_material: ShaderMaterial) -> Sprite2D:
	var texture: AtlasTexture = AtlasTexture.new()
	texture.atlas = source.texture
	texture.region = source.get_tile_texture_region(coords)
	var sprite: Sprite2D = Sprite2D.new()
	sprite.texture = texture
	sprite.material = shader_material
	return sprite


func _process(delta: float) -> void:
	elapsed += delta
	material_instance.set_shader_parameter("elapsed", elapsed)
	if elapsed >= LIFETIME:
		queue_free()
