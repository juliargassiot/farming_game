#!/usr/bin/env python3
"""Fails when a file's comment-only lines exceed max(10, 20% of its lines). Trailing comments do not count."""
import sys
from pathlib import Path

from pygments.lexers import get_lexer_for_filename
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, String, Text, Whitespace

ROOT = Path(__file__).resolve().parents[1]
CHECKED = {".gd", ".py", ".sh", ".gdshader", ".js", ".ts", ".c", ".cpp", ".h", ".rs", ".go"}
MIN_LINES = 10
RATIO = 0.2
SKIPPED = (Comment.Hashbang, Comment.Preproc, Comment.PreprocFile)


def lexer_for(path: Path):
    if path.suffix == ".gdshader":
        return get_lexer_by_name("glsl")
    return get_lexer_for_filename(path.name)


def comment_only_lines(path: Path, text: str) -> set[int]:
    with_comment, with_code = set(), set()
    line = 1
    for _, ttype, value in lexer_for(path).get_tokens_unprocessed(text):
        for offset, part in enumerate(value.split("\n")):
            if not part.strip():
                continue
            if ttype in SKIPPED:
                with_code.add(line + offset)
            elif ttype in Comment or ttype in String.Doc:
                with_comment.add(line + offset)
            elif ttype not in Whitespace and ttype is not Text.Whitespace:
                with_code.add(line + offset)
        line += value.count("\n")
    return with_comment - with_code


def check(path: Path) -> str | None:
    text = path.read_text(errors="replace")
    total = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    comments = comment_only_lines(path, text)
    allowed = max(MIN_LINES, int(total * RATIO))
    if len(comments) > allowed:
        return f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {len(comments)} comment lines, limit {allowed} for {total} lines"
    return None


def checkable(path: Path) -> bool:
    return path.suffix in CHECKED and path.is_file()


def main(argv: list[str]) -> int:
    paths = [Path(p.strip()) for p in sys.stdin.read().split("\n") if p.strip()] if "--stdin" in argv else [Path(p) for p in argv]
    problems = [check(p.resolve()) for p in paths if checkable(p)]
    problems = [p for p in problems if p]
    for problem in problems:
        print(problem)
    if problems:
        print("Fix by tightening or removing prose, not by padding code.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
