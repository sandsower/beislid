#!/usr/bin/env python3
"""Validate every skills/*/SKILL.md has required YAML frontmatter.

Requires `name` and `description` keys, both non-empty strings. Exits 1 on
any violation, printing one line per failure.
"""

from __future__ import annotations

import pathlib
import re
import sys


FRONTMATTER = re.compile(r"\A---\s*\n(.*?\n)---\s*\n", re.DOTALL)
KEY = re.compile(r"^([a-zA-Z_][\w-]*):\s*(.*)$")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    m = FRONTMATTER.match(text)
    if not m:
        return None
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = KEY.match(line)
        if not km:
            continue
        value = km.group(2).strip()
        if value.startswith(('"', "'")) and value.endswith(value[0]) and len(value) >= 2:
            value = value[1:-1]
        out[km.group(1)] = value
    return out


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
