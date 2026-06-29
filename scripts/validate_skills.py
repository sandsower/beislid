#!/usr/bin/env python3
"""Validate every skills/*/SKILL.md has required YAML frontmatter.

Requires `name` and `description` keys, both non-empty strings. Exits 1 on
any violation, printing one line per failure.
"""

from __future__ import annotations

import pathlib
import re
import sys


KEY = re.compile(r"^([a-zA-Z_][\w-]*):\s*(.*)$")
BLOCK_SCALAR = re.compile(r"^[>|](?:[+-])?(?:\s+#.*)?$")


def _strip_scalar(value: str) -> str:
    raw = value.rstrip()
    if not raw:
        return ""
    if raw[0] in {'"', "'"}:
        quote = raw[0]
        escaped = False
        for idx in range(1, len(raw)):
            ch = raw[idx]
            if quote == '"' and ch == "\\" and not escaped:
                escaped = True
                continue
            if ch == quote and not escaped:
                return raw[1:idx]
            escaped = False
        return raw[1:]
    comment = re.search(r"\s+#", raw)
    return (raw[: comment.start()] if comment else raw).rstrip()


def parse_frontmatter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip().lstrip("\ufeff") != "---":
        return None

    out: dict[str, str] = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            return out
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue

        km = KEY.match(line)
        if not km:
            i += 1
            continue

        key = km.group(1)
        raw = km.group(2).rstrip()
        if BLOCK_SCALAR.match(raw):
            block_lines: list[str] = []
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip() == "---":
                    break
                if not next_line.strip():
                    block_lines.append("")
                    i += 1
                    continue
                if next_line.startswith((" ", "\t")):
                    block_lines.append(next_line.lstrip(" \t"))
                    i += 1
                    continue
                break
            out[key] = "\n".join(block_lines).strip("\n")
            continue

        out[key] = _strip_scalar(raw)
        i += 1

    return None


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    errors: list[str] = []
    skill_files = sorted(root.glob("skills/*/SKILL.md"))
    if not skill_files:
        print(f"no skills found under {root}/skills", file=sys.stderr)
        return 1

    for path in skill_files:
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{rel}: missing YAML frontmatter")
            continue
        for key in ("name", "description"):
            if key not in fm:
                errors.append(f"{rel}: frontmatter missing `{key}`")
            elif not fm[key]:
                errors.append(f"{rel}: frontmatter `{key}` is empty")
        if "name" in fm:
            expected_dir = fm["name"].replace(":", "-")
            if expected_dir != path.parent.name:
                errors.append(
                    f"{rel}: frontmatter name `{fm['name']}` maps to dir `{expected_dir}`, got `{path.parent.name}`"
                )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print(f"ok: {len(skill_files)} skills validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
