#!/usr/bin/env python3
"""Claude Code hook. `post` checks the previous file once edits move to a different file; `stop` checks every file touched this session."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import comment_density  # noqa: E402


def state_path(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"farm-comment-density-{session_id or 'default'}.json"


def load_state(session_id: str) -> dict:
    path = state_path(session_id)
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {"last": None, "touched": [], "reported": {}}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def report(problems: list[str]) -> int:
    print("Comment density limit exceeded (tools/comment_density.py):\n" + "\n".join(problems)
          + "\nTighten or remove prose; do not pad code.", file=sys.stderr)
    return 2


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "post"
    payload = json.loads(sys.stdin.read() or "{}")
    state = load_state(payload.get("session_id", ""))
    code = 0
    if mode == "post":
        edited = payload.get("tool_input", {}).get("file_path")
        if not edited:
            return 0
        edited = str(Path(edited).resolve())
        if edited not in state["touched"]:
            state["touched"].append(edited)
        previous = state["last"]
        state["last"] = edited
        if previous and previous != edited and comment_density.checkable(Path(previous)):
            problem = comment_density.check(Path(previous))
            if problem:
                code = report([problem])
    elif mode == "stop":
        problems = []
        for touched in state["touched"]:
            path = Path(touched)
            if not comment_density.checkable(path):
                continue
            problem = comment_density.check(path)
            if problem and state["reported"].get(touched) != digest(path):
                state["reported"][touched] = digest(path)
                problems.append(problem)
        if problems and not payload.get("stop_hook_active"):
            code = report(problems)
    state_path(payload.get("session_id", "")).write_text(json.dumps(state))
    return code


if __name__ == "__main__":
    sys.exit(main())
