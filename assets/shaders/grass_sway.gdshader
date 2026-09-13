shader_type canvas_item;

uniform float elapsed = 0.0;
uniform float amplitude = 3.0;
uniform float direction = 1.0;

void vertex() {
	float swing = sin(elapsed * 18.0) * exp(-elapsed * 5.0);
	VERTEX.x += direction * amplitude * swing * (1.0 - UV.y);
}
