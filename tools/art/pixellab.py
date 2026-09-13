"""Thin client for the PixelLab v2 HTTP API (https://api.pixellab.ai/v2/docs)."""
import base64
import os
import time
from pathlib import Path

import requests

BASE_URL = "https://api.pixellab.ai/v2"
TOKEN_FILE = Path(__file__).with_name("token")
# The PixelLab account is shared with another game; everything this repo makes is named and tagged so the two stay apart.
PROJECT = "farming-game"
TAGS = [PROJECT]


def load_token() -> str:
    token = os.environ.get("PIXELLAB_TOKEN") or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else "")
    if not token:
        raise SystemExit("No PixelLab token: set PIXELLAB_TOKEN or write it to tools/art/token")
    return token


def b64_image(path: Path) -> dict:
    return {"type": "base64", "base64": base64.b64encode(path.read_bytes()).decode(), "format": "png"}


def b64_png(image) -> dict:
    import io
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return {"type": "base64", "base64": base64.b64encode(buffer.getvalue()).decode(), "format": "png"}


def decode_image(obj: dict) -> bytes:
    return base64.b64decode(obj["base64"])


class PixelLab:
    def __init__(self, token: str | None = None):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token or load_token()}"

    def call(self, method: str, path: str, **kwargs) -> dict:
        response = self.session.request(method, BASE_URL + path, timeout=300, **kwargs)
        if response.status_code >= 400:
            raise SystemExit(f"PixelLab {method} {path} -> {response.status_code}: {response.text[:800]}")
        return response.json()

    def balance(self) -> dict:
        return self.call("GET", "/balance")

    def create_image_pixen(self, description: str, size: tuple[int, int], **extra) -> dict:
        body = {"description": description, "image_size": {"width": size[0], "height": size[1]}, "no_background": True}
        body.update(extra)
        return self.call("POST", "/create-image-pixen", json=body)

    def create_character_v3(self, description: str, reference: Path, size: tuple[int, int], view: str, seed: int | None, name: str) -> dict:
        body = {"description": description, "reference_image": b64_image(reference), "image_size": {"width": size[0], "height": size[1]},
                "view": view, "name": f"{PROJECT}/{name}", "seed": seed}
        return self.call("POST", "/create-character-v3", json=body)

    def tag_character(self, character_id: str, tags: list[str] = ()) -> dict:
        return self.call("PATCH", f"/characters/{character_id}/tags", json={"tags": TAGS + [t for t in tags if t not in TAGS]})

    def create_character_animation(self, character_id: str, name: str, directions: list[str], action: str | None,
                                   template: str | None, frames: int, seed: int | None) -> dict:
        body = {"character_id": character_id, "animation_name": name, "directions": directions, "seed": seed}
        if template:
            body.update(mode="template", template_animation_id=template)
        else:
            body.update(mode="v3", action_description=action, frame_count=frames, keep_first_frame=False)
        return self.call("POST", "/characters/animations", json=body)

    def character(self, character_id: str) -> dict:
        return self.call("GET", f"/characters/{character_id}")

    def create_tileset(self, lower: str, upper: str, tile_size: int, transition_size: float, view: str, seed: int | None, **extra) -> dict:
        body = {"lower_description": lower, "upper_description": upper, "tile_size": {"width": tile_size, "height": tile_size},
                "transition_size": transition_size, "view": view, "seed": seed}
        body.update(extra)
        return self.call("POST", "/create-tileset", json=body)

    def tileset(self, tileset_id: str) -> dict:
        return self.call("GET", f"/tilesets/{tileset_id}")

    def job(self, job_id: str) -> dict:
        return self.call("GET", f"/background-jobs/{job_id}")

    def wait(self, job_ids: list[str], timeout: float = 1200, interval: float = 5) -> list[dict]:
        deadline = time.time() + timeout
        results = {}
        while len(results) < len(job_ids):
            for job_id in job_ids:
                if job_id in results:
                    continue
                state = self.job(job_id)
                if state["status"] == "completed":
                    results[job_id] = state
                elif state["status"] == "failed":
                    raise SystemExit(f"PixelLab job {job_id} failed: {state.get('last_response')}")
            if len(results) < len(job_ids):
                if time.time() > deadline:
                    raise SystemExit("PixelLab job timed out")
                time.sleep(interval)
        return [results[j] for j in job_ids]

    def download(self, url: str) -> bytes:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        return response.content
