"""Writes Godot text resources: SpriteFrames from sprite sheets and TileSets from atlases."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORNERS = ("NW", "NE", "SW", "SE")
CORNER_BITS = {"NW": "top_left_corner", "NE": "top_right_corner", "SW": "bottom_left_corner", "SE": "bottom_right_corner"}


def res_path(path) -> str:
    return "res://" + Path(path).relative_to(ROOT).as_posix() if Path(path).is_absolute() else "res://" + str(path)


def write_spriteframes(out: Path, animations: dict) -> None:
    """animations: name -> {"sheet": png path, "frame": (w, h), "frames": [indices], "fps": float, "loop": bool, "row": int}"""
    sheets = sorted({a["sheet"] for a in animations.values()})
    ext_ids = {sheet: str(i + 1) for i, sheet in enumerate(sheets)}
    lines, subs, entries = [], [], []
    for name in sorted(animations):
        a = animations[name]
        fw, fh = a["frame"]
        row = a.get("row", 0)
        textures = []
        for index in a["frames"]:
            sub_id = f"AtlasTexture_{name}_{index}"
            subs.append(f'[sub_resource type="AtlasTexture" id="{sub_id}"]\natlas = ExtResource("{ext_ids[a["sheet"]]}")\nregion = Rect2({index * fw}, {row * fh}, {fw}, {fh})\n')
            textures.append(f'{{\n"duration": 1.0,\n"texture": SubResource("{sub_id}")\n}}')
        loop = "true" if a.get("loop", True) else "false"
        entries.append(f'{{\n"frames": [{", ".join(textures)}],\n"loop": {loop},\n"name": &"{name}",\n"speed": {float(a.get("fps", 6)):.1f}\n}}')
    lines.append(f'[gd_resource type="SpriteFrames" load_steps={len(sheets) + len(subs) + 1} format=3]\n')
    for sheet in sheets:
        lines.append(f'[ext_resource type="Texture2D" path="{res_path(sheet)}" id="{ext_ids[sheet]}"]')
    lines.append("")
    lines.extend(subs)
    lines.append("[resource]\nanimations = [" + ", ".join(entries) + "]\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))


def write_tileset(out: Path, atlas: Path, tile: int, columns: int, rows: int, solid=(), terrains=None, tile_terrain=None, animations=None) -> None:
    """terrains: [names]; tile_terrain: {(col,row): {"NW": idx, ...}} for Match Corners autotiling; animations: {(col,row): [seconds per frame]},
    frames laid out to the right of the tile, which then owns those columns."""
    owned = {(c + i, r) for (c, r), durations in (animations or {}).items() for i in range(1, len(durations))}
    lines = [f'[gd_resource type="TileSet" load_steps=3 format=3]\n', f'[ext_resource type="Texture2D" path="{res_path(atlas)}" id="1"]\n']
    lines.append('[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_1"]\ntexture = ExtResource("1")\ntexture_region_size = Vector2i(%d, %d)' % (tile, tile))
    half = tile / 2
    for r in range(rows):
        for c in range(columns):
            if (tile_terrain is not None and (c, r) not in tile_terrain) or (c, r) in owned:
                continue
            key = f"{c}:{r}/0"
            if animations and (c, r) in animations and len(animations[(c, r)]) > 1:
                lines.append(f"{c}:{r}/animation_columns = 0\n{c}:{r}/animation_frames_count = {len(animations[(c, r)])}")
                for i, seconds in enumerate(animations[(c, r)]):
                    lines.append(f"{c}:{r}/animation_frame_{i}/duration = {seconds:.2f}")
            lines.append(f"{key} = 0")
            if (c + r * columns) in solid or (c, r) in solid:
                lines.append(f"{key}/physics_layer_0/polygon_0/points = PackedVector2Array({-half}, {-half}, {half}, {-half}, {half}, {half}, {-half}, {half})")
            if tile_terrain and (c, r) in tile_terrain:
                corners = tile_terrain[(c, r)]
                lines.append(f"{key}/terrain_set = 0")
                lines.append(f"{key}/terrain = {max(set(corners.values()), key=list(corners.values()).count)}")
                for corner, idx in corners.items():
                    lines.append(f"{key}/terrains_peering_bit/{CORNER_BITS[corner]} = {idx}")
    lines.append(f"\n[resource]\ntile_size = Vector2i({tile}, {tile})")
    if solid:
        lines.append("physics_layer_0/collision_layer = 1\nphysics_layer_0/collision_mask = 1")
    if terrains:
        lines.append("terrain_set_0/mode = 1")
        for i, name in enumerate(terrains):
            lines.append(f'terrain_set_0/terrain_{i}/name = "{name}"\nterrain_set_0/terrain_{i}/color = Color({0.3 + 0.4 * i}, 0.6, 0.3, 1)')
    lines.append('sources/0 = SubResource("TileSetAtlasSource_1")\n')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
