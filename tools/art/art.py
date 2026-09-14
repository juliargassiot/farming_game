#!/usr/bin/env python3
"""Art pipeline. Run `tools/art/art.py --help`; the workflow is described in tools/art/README.md."""
import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import godot_res  # noqa: E402
import grid_to_png  # noqa: E402
import sheets  # noqa: E402
import tiles_post  # noqa: E402
from pixellab import PixelLab, b64_image, b64_png, decode_image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "tools" / "art"
RAW = ART / "raw"
PREVIEWS = ROOT / "previews" / "art"
DIRECTIONS = ["south", "south-east", "east", "north-east", "north", "north-west", "west", "south-west"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_generated(data: dict) -> None:
    (ART / "generated.json").write_text(json.dumps(data, indent=2) + "\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def save_png(data: bytes, path: Path) -> Image.Image:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return Image.open(path).convert("RGBA")


def frame_size(body: dict) -> tuple[int, int]:
    size = body["size"]
    return (size, size) if isinstance(size, int) else (size[0], size[1])


def record_for(generated: dict, kind: str, name: str) -> dict:
    return generated[kind].setdefault(name, {"approved": False})


def require_approved(record: dict, name: str) -> None:
    design = record.get("design")
    if not design:
        raise SystemExit(f"{name}: no design yet; run `design {name}` first")
    if not record.get("approved") or record.get("approved_hash") != design.get("hash"):
        raise SystemExit(f"{name}: design is not approved. Show previews/art/{name}-design.png and wait for a yes.")


def cmd_placeholders(_args) -> None:
    for path in grid_to_png.convert_all():
        print("wrote", rel(path))
    manifest = load_json(ART / "placeholders.json")
    for out, spec in manifest["spriteframes"].items():
        animations = {name: dict(a, frame=spec["frame"], fps=a.get("fps", spec.get("fps", 6))) for name, a in spec["animations"].items()}
        godot_res.write_spriteframes(ROOT / out, animations)
        print("wrote", out)
    for out, spec in manifest["tilesets"].items():
        godot_res.write_tileset(ROOT / out, Path(spec["atlas"]), spec["tile"], spec["columns"], spec["rows"], solid=spec.get("solid", ()))
        print("wrote", out)


def cmd_balance(_args) -> None:
    print(json.dumps(PixelLab().balance(), indent=2))


def cmd_tag(_args) -> None:
    client = PixelLab()
    for name, record in load_json(ART / "generated.json")["characters"].items():
        if record.get("character_id"):
            print(name, client.tag_character(record["character_id"], [name])["tags"])


def cmd_status(_args) -> None:
    generated = load_json(ART / "generated.json")
    for kind in ("characters", "tilesets"):
        for name, record in generated[kind].items():
            stage = "design" if "design" in record else "none"
            if record.get("character_id") or record.get("tileset_id"):
                stage = "rotated" if kind == "characters" else "generated"
            if record.get("animations"):
                stage = "animated: " + ", ".join(record["animations"])
            if record.get("imported"):
                stage = "imported " + record["imported"]
            print(f"{kind[:-1]:9} {name:16} approved={record.get('approved', False)!s:5} {stage}")


def cmd_design(args) -> None:
    body = load_json(ART / "bodies.json")[args.name]
    generated = load_json(ART / "generated.json")
    record = record_for(generated, "characters", args.name)
    raw = RAW / args.name / "design.png"
    if args.source:
        response = {}
        image = save_png(Path(args.source).read_bytes(), raw)
    else:
        response = PixelLab().create_image_pixen(body["description"], frame_size(body), view=body.get("view", "low top-down"), direction="south",
                                                 outline=body.get("outline"), detail=body.get("detail"), seed=args.seed)
        image = save_png(decode_image(response["image"]), raw)
    preview = PREVIEWS / f"{args.name}-design.png"
    preview.parent.mkdir(parents=True, exist_ok=True)
    sheets.upscaled(image, 3).save(preview)
    record.update(approved=False, approved_hash=None, character_id=None, rotations=None, animations={}, imported=None,
                  design={"file": rel(raw), "preview": rel(preview), "prompt": body["description"], "size": frame_size(body),
                          "seed": args.seed, "source": args.source, "usage": response.get("usage"), "created": now(), "hash": sha(raw)})
    save_generated(generated)
    print(f"Design written to {rel(preview)}. Stop here and ask for approval.")


def cmd_candidates(args) -> None:
    """Sweep seeds and views (or prompt overrides) into one numbered sheet; winners are adopted with `design --source`."""
    body = load_json(ART / "bodies.json")[args.name]
    client = PixelLab()
    folder = RAW / args.name / "candidates"
    prompts = [line for line in Path(args.prompts).read_text().splitlines() if line.strip()] if args.prompts else [body["description"]]
    frames = []
    for view in args.views.split(","):
        for seed in [int(x) for x in args.seeds.split(",")]:
            for i, prompt in enumerate(prompts):
                response = client.create_image_pixen(prompt, frame_size(body), view=view, direction="south", outline=body.get("outline"),
                                                     detail=body.get("detail"), seed=seed)
                path = folder / f"{view.replace(' ', '_')}-{seed}-{i}.png"
                frames.append(save_png(decode_image(response["image"]), path))
                print(f"{len(frames)}: {rel(path)}")
    preview = PREVIEWS / f"{args.name}-candidates.png"
    preview.parent.mkdir(parents=True, exist_ok=True)
    sheets.contact_sheet([("", frames)], scale=2).save(preview)
    if args.face:
        sheets.face_strip(frames, tuple(int(v) for v in args.face.split(","))).save(PREVIEWS / f"{args.name}-face.png")
    print(f"Sheet at {rel(preview)}; numbers match the list above")


def cmd_edit(args) -> None:
    """Surgical text edit of one PNG through edit-image-pixen; pose and untouched pixels are preserved."""
    client = PixelLab()
    source = Path(args.source)
    response = client.call("POST", "/edit-image-pixen", json={"image": b64_image(source), "description": args.instruction, "seed": args.seed,
                                                              "no_background": True})
    result = client.wait([response["background_job_id"]])[0]
    out = RAW / args.name / "edits" / f"{source.stem}-{sha(source)}.png"
    image = save_png(decode_image(result["last_response"]["image"]), out)
    preview = PREVIEWS / f"{args.name}-edit.png"
    sheets.contact_sheet([("before", [Image.open(source).convert("RGBA")]), ("after", [image])], scale=3).save(preview)
    print(f"Edit written to {rel(out)}; compare at {rel(preview)}")


def cmd_crop_design(args) -> None:
    """One 32×32 image per crop for a growth stage, from tools/art/crops.json; all crops of a season land on one sheet."""
    specs = load_json(ART / "crops.json")
    crops = load_json(ROOT / "data" / "crops.json")
    generated = load_json(ART / "generated.json")
    client = PixelLab()
    names = [n for n in crops if n in specs and (args.season is None or args.season in crops[n].get("seasons", []))]
    if args.name:
        names = [args.name]
    frames = []
    for name in names:
        spec, out = specs[name], RAW / "crops" / name / f"{args.stage}.png"
        if args.stage == "seed":
            seeds = specs["_seed_styles"][spec["seed"]].format(colour=spec["colour"])
            prompt = f"{seeds} a small mound of dark tilled soil, seeds only, no plant, no leaves, no sprout, no flower, seen from above, pixel art, nothing else"
        else:
            stage_text = {"sprout": "a tiny seedling with two small leaves, just emerged", "growing": "a young plant, half grown, leafy with at most one tightly closed bud, no open flowers, no fruit",
                          "ready": "fully grown and ready to harvest"}.get(args.stage, args.stage)
            subject = f"{stage_text}, leaves tinged {spec['colour']}" if args.stage == "sprout" else f"{spec['final']}: {stage_text}, hints of {spec['colour']}"
            subject = spec.get("stage_prompts", {}).get(args.stage, subject)
            prompt = f"{subject}, no open flower, no fruit, on a small round mound of dark tilled soil, seen from above, pixel art, nothing else"
        if not (out.exists() and not args.redo):
            response = client.create_image_pixen(prompt, (32, 32), view="high top-down", outline="lineless", detail="medium detail", seed=args.seed)
            save_png(decode_image(response["image"]), out)
            record = generated.setdefault("crops", {}).setdefault(name, {"approved": False})
            record.setdefault("stages", {})[args.stage] = {"file": rel(out), "prompt": prompt, "seed": args.seed, "created": now(), "hash": sha(out)}
        frames.append((name, [Image.open(out).convert("RGBA")]))
        print(f"{name}: {rel(out)}")
    preview = PREVIEWS / f"crops-{args.stage}.png"
    sheets.labelled_grid([(name, ims[0]) for name, ims in frames]).save(preview)
    save_generated(generated)
    print(f"Sheet at {rel(preview)}. Stop here and ask for approval.")


def cmd_crop_import(args) -> None:
    """Atlas row per crop, one animated tile per stage laid out left to right; data/crop_atlas.json says where each stage starts."""
    import crop_anim
    specs = load_json(ART / "crops.json")
    generated = load_json(ART / "generated.json")
    rows, layout, animations = [], {}, {}
    for name, record in generated.get("crops", {}).items():
        stages = [st for st in STAGE_ORDER if st in record.get("stages", {})]
        if any(not record["stages"][st].get("approved") for st in stages):
            raise SystemExit(f"{name}: stage {[st for st in stages if not record['stages'][st].get('approved')][0]} is not approved")
        frames_by_stage = []
        for st in stages:
            image = Image.open(ROOT / record["stages"][st]["file"]).convert("RGBA")
            kind = specs.get(name, {}).get("anim", {}).get(st)
            frames_by_stage.append(crop_anim.BUILDERS[kind](image) if kind else [(image, 1.0)])
        rows.append((name, stages, frames_by_stage))
    size = 32
    width = max(sum(len(f) for f in frames) for _, _, frames in rows)
    atlas = Image.new("RGBA", (width * size, len(rows) * size), (0, 0, 0, 0))
    for r, (name, stages, frames_by_stage) in enumerate(rows):
        col, starts = 0, []
        for frames in frames_by_stage:
            starts.append(col)
            animations[(col, r)] = [seconds for _, seconds in frames]
            for image, _ in frames:
                atlas.alpha_composite(image, (col * size, r * size))
                col += 1
        layout[name] = {"row": r, "stages": dict(zip(stages, starts))}
    out_png = ROOT / "assets" / "tiles" / "crops.png"
    atlas.save(out_png)
    godot_res.write_tileset(out_png.with_suffix(".tres"), out_png, size, width, len(rows), animations=animations)
    (ROOT / "data" / "crop_atlas.json").write_text(json.dumps(layout, indent=1) + "\n")
    print(f"Wrote {rel(out_png)} with {len(rows)} crops; stage columns in data/crop_atlas.json")


STAGE_ORDER = ["seed", "sprout", "growing", "ready", "picked"]


def cmd_approve(args) -> None:
    generated = load_json(ART / "generated.json")
    if args.name == "crops":
        for name, record in generated.get("crops", {}).items():
            if args.stage in record.get("stages", {}):
                record["stages"][args.stage]["approved"] = not args.reject
        save_generated(generated)
        print(f"crops/{args.stage}: {'rejected' if args.reject else 'approved'}")
        return
    kind = "tilesets" if args.name in generated["tilesets"] and args.name not in generated["characters"] else "characters"
    record = generated[kind].get(args.name)
    if not record or "design" not in record:
        raise SystemExit(f"{args.name}: nothing to approve")
    record.update(approved=not args.reject, approved_hash=None if args.reject else record["design"]["hash"],
                  approval_note=args.note or "", approved_at=now())
    save_generated(generated)
    print(f"{args.name}: {'rejected' if args.reject else 'approved'}")


def cmd_rotate(args) -> None:
    body = load_json(ART / "bodies.json")[args.name]
    generated = load_json(ART / "generated.json")
    record = record_for(generated, "characters", args.name)
    require_approved(record, args.name)
    client = PixelLab()
    response = client.create_character_v3(body["description"], ROOT / record["design"]["file"], frame_size(body), body.get("view", "low top-down"),
                                          args.seed, args.name)
    client.wait([response["background_job_id"]])
    client.tag_character(response["character_id"], [args.name])
    details = client.character(response["character_id"])
    rows = []
    for direction in body["directions"]:
        url = details["rotation_urls"][direction]
        image = save_png(client.download(url), RAW / args.name / "rotations" / f"{direction}.png")
        rows.append((direction, [image]))
    preview = PREVIEWS / f"{args.name}-rotations.png"
    sheets.contact_sheet(rows).save(preview)
    record.update(character_id=response["character_id"],
                  rotations={"job": response["background_job_id"], "usage": response.get("usage"), "created": now(),
                             "directions": body["directions"], "preview": rel(preview)})
    save_generated(generated)
    print(f"Rotations written to {rel(preview)}")


def cmd_animate(args) -> None:
    body = load_json(ART / "bodies.json")[args.name]
    generated = load_json(ART / "generated.json")
    record = record_for(generated, "characters", args.name)
    require_approved(record, args.name)
    if not record.get("character_id"):
        raise SystemExit(f"{args.name}: run `rotate {args.name}` first")
    client = PixelLab()
    names = [args.animation] if args.animation else list(body["animations"])
    directions = [args.direction] if args.direction else body["directions"]
    for anim_name in names:
        spec = body["animations"][anim_name]
        jobs = []
        for action in {spec.get("actions", {}).get(d, spec.get("action")) for d in directions} if not args.fetch else ():
            batch = [d for d in directions if spec.get("actions", {}).get(d, spec.get("action")) == action]
            response = client.create_character_animation(record["character_id"], anim_name, batch, action, spec.get("template"),
                                                         spec.get("frames", 8), args.seed)
            jobs += response["background_job_ids"]
        client.wait(jobs)
        details = client.character(record["character_id"])
        wanted = {anim_name, spec.get("template")} - {None}
        groups = [g for g in details.get("animations", []) if g.get("display_name") in wanted or g.get("animation_type") in wanted]
        if not groups:
            raise SystemExit(f"{args.name}: animation {anim_name} not found on character {record['character_id']}")
        previous = record.get("animations", {}).get(anim_name, {})
        windows = dict(previous.get("directions", {}))
        pending = set(directions)
        for entry in [e for g in groups for e in g["directions"]]:
            direction = entry["direction"]
            if direction not in pending:
                continue
            pending.discard(direction)
            folder = RAW / args.name / "animations" / anim_name / direction
            for old in folder.glob("*.png"):
                old.unlink()
            for i, url in enumerate(entry["frames"]):
                save_png(client.download(url), folder / f"{i:03d}.png")
            windows[direction] = {"from": 0, "to": len(entry["frames"]) - 1}
        rows = [(d, [Image.open(f).convert("RGBA") for f in sorted((RAW / args.name / "animations" / anim_name / d).glob("*.png"))])
                for d in body["directions"] if d in windows]
        preview = PREVIEWS / f"{args.name}-{anim_name}.png"
        sheets.contact_sheet(rows).save(preview)
        record.setdefault("animations", {})[anim_name] = {"jobs": previous.get("jobs", []) + jobs, "created": now(),
                                                          "fps": spec.get("fps", 8), "directions": windows, "preview": rel(preview)}
        save_generated(generated)
        print(f"{anim_name}: contact sheet at {rel(preview)}; judge it and record windows with `trim`")


def cmd_trim(args) -> None:
    generated = load_json(ART / "generated.json")
    anim = generated["characters"][args.name]["animations"][args.animation]
    targets = list(anim["directions"]) if args.direction == "all" else [args.direction]
    for direction in targets:
        anim["directions"][direction] = {"from": args.start, "to": args.end}
    save_generated(generated)
    print(f"{args.name}/{args.animation}: frames {args.start}-{args.end} kept for {', '.join(targets)}")


def cmd_import(args) -> None:
    body = load_json(ART / "bodies.json")[args.name]
    generated = load_json(ART / "generated.json")
    record = record_for(generated, "characters", args.name)
    require_approved(record, args.name)
    out_dir = ROOT / "assets" / "characters" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    animations = {}
    rotation_frames = {d: Image.open(RAW / args.name / "rotations" / f"{d}.png").convert("RGBA") for d in body["directions"]}
    size = frame_size(body)
    animations.update(_write_sheet(out_dir / "rotations.png", "stand", body["directions"], {d: [rotation_frames[d]] for d in body["directions"]}, 1, size))
    for anim_name, anim in record.get("animations", {}).items():
        per_direction = {}
        for direction in body["directions"]:
            window = anim["directions"][direction]
            folder = RAW / args.name / "animations" / anim_name / direction
            files = sorted(folder.glob("*.png"))[window["from"]:window["to"] + 1]
            per_direction[direction] = [Image.open(f).convert("RGBA") for f in files]
        animations.update(_write_sheet(out_dir / f"{anim_name}.png", anim_name, body["directions"], per_direction, anim.get("fps", 8), size))
    godot_res.write_spriteframes(out_dir / f"{args.name}.tres", animations)
    record["imported"] = now()
    save_generated(generated)
    print(f"Imported {len(animations)} animations into {rel(out_dir)}")


def _fit(frame: Image.Image, size: tuple[int, int]) -> Image.Image:
    """PixelLab returns animation frames centered on a larger canvas; crop or pad back to the body's frame size."""
    if frame.size == size:
        return frame
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.alpha_composite(frame, ((size[0] - frame.width) // 2, (size[1] - frame.height) // 2)) if frame.width <= size[0] and frame.height <= size[1] \
        else out.alpha_composite(frame.crop(((frame.width - size[0]) // 2, (frame.height - size[1]) // 2, (frame.width + size[0]) // 2, (frame.height + size[1]) // 2)))
    return out


def _write_sheet(out: Path, anim_name: str, directions: list[str], frames_by_direction: dict, fps: float, size: tuple[int, int]) -> dict:
    frames_by_direction = {d: [_fit(f, size) for f in frames] for d, frames in frames_by_direction.items()}
    cell_w, cell_h = size
    columns = max(len(frames) for frames in frames_by_direction.values())
    sheet = Image.new("RGBA", (columns * cell_w, len(directions) * cell_h), (0, 0, 0, 0))
    animations = {}
    for row, direction in enumerate(directions):
        frames = frames_by_direction[direction]
        for col, frame in enumerate(frames):
            sheet.alpha_composite(frame, (col * cell_w + (cell_w - frame.width) // 2, row * cell_h + (cell_h - frame.height) // 2))
        animations[f"{anim_name}_{direction}"] = {"sheet": rel(out), "frame": (cell_w, cell_h), "frames": list(range(len(frames))), "row": row, "fps": fps}
    sheet.save(out)
    return animations


def _season_specs(spec: dict, season: str | None) -> dict:
    seasons = spec.get("seasons", {"": {}})
    if season:
        seasons = {season: seasons[season]}
    return {key: dict(spec, **override) for key, override in seasons.items()}


def _tile_folder(name: str, season: str, spec: dict | None = None) -> Path:
    """A season may borrow another season's generated tiles (`tiles_from`) and restyle them."""
    season = (spec or {}).get("tiles_from", season)
    return RAW / "tiles" / name / season if season else RAW / "tiles" / name


def _load_tiles(folder: Path) -> tuple[dict, list]:
    tiles = {int(p.stem): Image.open(p).convert("RGBA") for p in folder.glob("[0-9][0-9].png")}
    variants = [Image.open(p).convert("RGBA") for p in sorted(folder.glob("variant-*.png"))]
    return tiles, variants


def _assemble(folder: Path, sspec: dict) -> dict:
    """Finished tile groups for one season: field (lower ↔ untilled), variants, tilled cutouts, and the same cutouts tinted wet."""
    raw_tiles, raw_variants = _load_tiles(folder)
    tiles, blended = tiles_post.finish(raw_tiles, raw_variants, sspec)
    size = sspec.get("tile_size", 16)
    lower, upper = tiles_post.mean_colour(tiles[0]), tiles_post.mean_colour(tiles[15])
    lower_target = tiles_post.hex_colour(sspec["lower_colour"]) if sspec.get("lower_colour") else lower
    tiles = tiles_post.recolour(tiles, lower, upper, lower_target, None)
    tiles = tiles_post.season_style(tiles, lower_target, upper, sspec.get("style", {}))
    if sspec.get("variants"):
        variants = raw_variants if sspec.get("variant_mode") == "sprite" else [tiles_post.recolour({0: t}, lower, upper, lower_target, None)[0] for t in blended]
    else:
        textured = tiles_post.texture_variants(tiles[0], lower_target, sspec.get("variant_count", 6), sspec.get("variant_radius", 15))
        plain_dots = {"dots": ["#%02x%02x%02x" % tuple(int(v) for v in lower_target)]}
        blades = [tiles_post.season_style({0: t}, lower_target, upper, plain_dots)[0] for t in textured]
        flowered = tiles_post.add_dots(textured, sspec.get("style", {}).get("dots", []), sspec.get("flower_dots", 0), sspec.get("variant_radius", 15))
        variants = flowered + blades
    field = tiles_post.recolour(tiles, lower_target, upper, None, tiles_post.hex_colour(sspec["field_colour"]), sspec.get("field_flatten", 0.0))
    field[0] = tiles_post.flat_tile(lower_target, size)
    tilled = tiles_post.cutout(tiles, lower_target, upper)
    wet = tiles_post.tint(tilled, tiles_post.hex_colour(sspec.get("wet_tint", "#ffffff")) / 255)
    return {"field": field, "variants": variants, "tilled": tilled, "wet": wet}


def _tile_preview(name: str, spec: dict) -> Path:
    panels = []
    for season, sspec in _season_specs(spec, None).items():
        folder = _tile_folder(name, season, sspec)
        if not (folder / "00.png").exists():
            continue
        groups = _assemble(folder, sspec)
        size = sspec.get("tile_size", 16)
        field = tiles_post.demo_field(groups["field"], groups["variants"], size)
        tilled = tiles_post.demo_field(groups["tilled"], [], size, mark=tiles_post.DEMO_TILLED)
        field.alpha_composite(tilled)
        strip = [groups["field"][0]] + groups["variants"]
        panel = Image.new("RGBA", (field.width + len(strip) * (size + 4) + 20, field.height + 16), (40, 40, 48, 255))
        panel.alpha_composite(field, (8, 8))
        for i, tile in enumerate(strip):
            panel.alpha_composite(tile, (field.width + 16 + i * (size + 4), 8))
        ImageDraw.Draw(panel).text((field.width + 16, size + 12), season or name, fill=(230, 230, 230, 255))
        panels.append(panel)
    sheet = Image.new("RGBA", (max(p.width for p in panels), sum(p.height + 4 for p in panels)), (40, 40, 48, 255))
    y = 0
    for panel in panels:
        sheet.alpha_composite(panel, (0, y))
        y += panel.height + 4
    preview = PREVIEWS / f"{name}-design.png"
    preview.parent.mkdir(parents=True, exist_ok=True)
    sheets.upscaled(sheet, 3).save(preview)
    return preview


def _inpaint_variants(client: PixelLab, base: Image.Image, prompts: list[str], seed: int) -> list[Image.Image]:
    """Paint each prompt into the centre of the plain lower tile, seen inside a 3×3 tiling so it stays seamless."""
    size = base.width
    context = Image.new("RGBA", (3 * size, 3 * size))
    for y in range(3):
        for x in range(3):
            context.alpha_composite(base, (x * size, y * size))
    mask = Image.new("RGB", context.size, "black")
    ImageDraw.Draw(mask).ellipse([size + 5, size + 7, 2 * size - 6, 2 * size - 8], fill="white")
    payload = lambda img: {"image": b64_png(img), "size": {"width": img.width, "height": img.height}}  # noqa: E731
    jobs = [client.call("POST", "/inpaint-v3", json={"description": p, "inpainting_image": payload(context), "mask_image": payload(mask), "seed": seed + i})["background_job_id"]
            for i, p in enumerate(prompts)]
    out = []
    for result in client.wait(jobs):
        response = result["last_response"]
        image = Image.open(io.BytesIO(decode_image(response.get("image") or response["images"][0]))).convert("RGBA")
        out.append(image.crop((size, size, 2 * size, 2 * size)))
    return out


def _sprite_variants(client: PixelLab, colour, tile: int, sprite: int, prompts: list[str], seed: int) -> list[Image.Image]:
    """One transparent sprite per prompt, dropped onto a flat tile at a seeded offset so scattered variants don't line up."""
    import random
    rng = random.Random(seed)
    out = []
    for i, prompt in enumerate(prompts):
        response = client.create_image_pixen(f"{prompt}, seen from above, small, alone, nothing else", (sprite, sprite), view="high top-down",
                                             outline="lineless", detail="medium detail", seed=seed + i)
        image = Image.open(io.BytesIO(decode_image(response["image"]))).convert("RGBA")
        box = image.getbbox() or (0, 0, sprite, sprite)
        image = image.crop(box)
        base = tiles_post.flat_tile(colour, tile)
        x = rng.randint(1, max(1, tile - image.width - 1))
        y = rng.randint(1, max(1, tile - image.height - 1))
        base.alpha_composite(image, (x, y))
        out.append(base)
    return out


def cmd_tile_design(args) -> None:
    spec = load_json(ART / "tiles.json")[args.name]
    generated = load_json(ART / "generated.json")
    record = record_for(generated, "tilesets", args.name)
    client = PixelLab()
    for season, sspec in _season_specs(spec, args.season).items():
        folder = _tile_folder(args.name, season)
        seed = args.seed if args.seed is not None else sspec.get("seed")
        if not args.variants_only:
            response = client.create_tileset(sspec["lower"], sspec["upper"], sspec.get("tile_size", 16), sspec.get("transition_size", 0.0),
                                             sspec.get("view", "high top-down"), seed, **sspec.get("params", {}))
            client.wait([response["background_job_id"]])
            tileset = client.tileset(response["tileset_id"])
            for tile in tileset["tileset"]["tiles"]:
                save_png(decode_image(tile["image"]), folder / f"{_corner_index(tile['corners']):02d}.png")
            (folder / "tileset.json").write_text(json.dumps({"id": response["tileset_id"], "metadata": tileset["metadata"]}, indent=1))
        base = Image.open(folder / "00.png").convert("RGBA")
        if sspec.get("variant_mode") == "sprite":
            colour = tiles_post.hex_colour(sspec["lower_colour"]) if sspec.get("lower_colour") else tiles_post.mean_colour(base)
            variants = _sprite_variants(client, colour, base.width, sspec.get("variant_size", 16), sspec.get("variants", []), (seed or 0) + 100)
        else:
            variants = _inpaint_variants(client, base, sspec.get("variants", []), (seed or 0) + 100)
        for old in folder.glob("variant-*.png"):
            old.unlink()
        for i, image in enumerate(variants):
            save_png(_png_bytes(image), folder / f"variant-{i}.png")
        print(f"{args.name}/{season or 'base'}: tiles in {rel(folder)}")
    preview = _tile_preview(args.name, spec)
    record.update(approved=False, approved_hash=None, imported=None,
                  design={"file": rel(RAW / "tiles" / args.name), "preview": rel(preview), "created": now(), "seed": spec.get("seed"),
                          "hash": sha(_tile_folder(args.name, next(iter(_season_specs(spec, None)))) / "00.png")})
    save_generated(generated)
    print(f"Tileset preview written to {rel(preview)}. Stop here and ask for approval.")


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _corner_index(corners: dict) -> int:
    return sum((1 << (3 - i)) for i, key in enumerate(("NW", "NE", "SW", "SE")) if corners[key] == "upper")


def cmd_tile_import(args) -> None:
    """Atlas rows 0-3: lower ↔ untilled field Wang tiles (index 0 flat lower colour); rows 4-6: variants (flowered, then blades); rows 7-10: tilled cutouts; rows 11-14: wet cutouts."""
    spec = load_json(ART / "tiles.json")[args.name]
    generated = load_json(ART / "generated.json")
    record = record_for(generated, "tilesets", args.name)
    require_approved(record, args.name)
    size = spec.get("tile_size", 16)
    for season, sspec in _season_specs(spec, None).items():
        groups = _assemble(_tile_folder(args.name, season, sspec), sspec)
        blocks = [(groups["field"], 0, 1), (dict(enumerate(groups["variants"])), 4, 0), (groups["tilled"], 7, 1), (groups["wet"], 11, 1)]
        atlas = Image.new("RGBA", (4 * size, 15 * size), (0, 0, 0, 0))
        terrain = {}
        for block, first_row, upper_bit in blocks:
            for index, tile in block.items():
                col, row = index % 4, first_row + index // 4
                atlas.alpha_composite(tile, (col * size, row * size))
                terrain[(col, row)] = {key: ((index >> (3 - i)) & 1) * upper_bit for i, key in enumerate(("NW", "NE", "SW", "SE"))}
        out_png = ROOT / "assets" / "tiles" / (f"{args.name}_{season}.png" if season else f"{args.name}.png")
        out_png.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(out_png)
        godot_res.write_tileset(out_png.with_suffix(".tres"), out_png, size, 4, 15, terrains=[spec.get("lower_name", "lower"), spec.get("upper_name", "upper")],
                                tile_terrain=terrain)
        print(f"Wrote {rel(out_png)} and {rel(out_png.with_suffix('.tres'))}")
    record["imported"] = now()
    save_generated(generated)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("placeholders", help="convert tools/art/grids to PNGs and write placeholder resources").set_defaults(func=cmd_placeholders)
    sub.add_parser("balance", help="show PixelLab credits").set_defaults(func=cmd_balance)
    sub.add_parser("status", help="list every generated asset and its stage").set_defaults(func=cmd_status)
    sub.add_parser("tag", help="re-apply the farming-game tags to every stored PixelLab character").set_defaults(func=cmd_tag)
    for name, func, needs_seed in (("design", cmd_design, True), ("rotate", cmd_rotate, True), ("import", cmd_import, False),
                                   ("tile-design", cmd_tile_design, True), ("tile-import", cmd_tile_import, False)):
        p = sub.add_parser(name)
        p.add_argument("name")
        if needs_seed:
            p.add_argument("--seed", type=int)
        if name == "design":
            p.add_argument("--source", help="adopt a hand-edited PNG as the design instead of generating one")
        if name == "tile-design":
            p.add_argument("--season", help="one season from tiles.json instead of all")
            p.add_argument("--variants-only", action="store_true", help="keep the tiles on disk and only repaint the variants")
        p.set_defaults(func=func)
    p = sub.add_parser("candidates", help="sweep seeds/views/prompts into one numbered sheet")
    p.add_argument("name")
    p.add_argument("--seeds", default="22,33")
    p.add_argument("--views", default="low top-down")
    p.add_argument("--prompts", help="text file, one prompt per line, overriding the body description")
    p.add_argument("--face", help="x0,y0,x1,y1 box to show at 8x in <name>-face.png")
    p.set_defaults(func=cmd_candidates)
    p = sub.add_parser("crop-design", help="generate one growth stage for every crop of a season")
    p.add_argument("stage", help="seed, sprout, growing, ready, ...")
    p.add_argument("--season")
    p.add_argument("--name", help="one crop only")
    p.add_argument("--seed", type=int)
    p.add_argument("--redo", action="store_true", help="regenerate even when the stage exists")
    p.set_defaults(func=cmd_crop_design)
    sub.add_parser("crop-import", help="write the crop atlas, animated tiles, and stage layout").set_defaults(func=cmd_crop_import)
    p = sub.add_parser("edit", help="text edit of one PNG, keeping everything else")
    p.add_argument("name")
    p.add_argument("source")
    p.add_argument("instruction")
    p.add_argument("--seed", type=int)
    p.set_defaults(func=cmd_edit)
    p = sub.add_parser("animate")
    p.add_argument("name")
    p.add_argument("animation", nargs="?")
    p.add_argument("--direction", help="redo one direction and keep the others")
    p.add_argument("--fetch", action="store_true", help="download frames already on the character instead of generating")
    p.add_argument("--seed", type=int)
    p.set_defaults(func=cmd_animate)
    p = sub.add_parser("approve", help="record the user's yes (or --reject) for a design")
    p.add_argument("name")
    p.add_argument("--reject", action="store_true")
    p.add_argument("--note")
    p.add_argument("--stage", help="with name `crops`: the growth stage being approved")
    p.set_defaults(func=cmd_approve)
    p = sub.add_parser("trim", help="record which frames of an animation to keep")
    p.add_argument("name")
    p.add_argument("animation")
    p.add_argument("direction", help="a direction name or 'all'")
    p.add_argument("start", type=int)
    p.add_argument("end", type=int)
    p.set_defaults(func=cmd_trim)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
