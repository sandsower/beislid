#!/usr/bin/env python3
"""Validate the repo's guide/feedforward registry and guide paths.

Guides are feedforward context, not gates: they shape what an orchestrator
loads before a stage, and the registry should point at real, readable Markdown
artifacts.
"""

from __future__ import annotations

import pathlib
import re
import sys

ALLOWED_STAGES = {
    "kickoff",
    "spec",
    "blueprint",
    "implement",
    "review",
}


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_inline_list(raw: str) -> list[str] | None:
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        return None
    inner = raw[1:-1].strip()
    if not inner:
        return []
    return [strip_quotes(item) for item in inner.split(",") if strip_quotes(item)]


def extract_block(text: str) -> str:
    match = re.search(r"```beislid:guides\s*\n([\s\S]*?)\n```", text)
    if not match:
        return ""
    return match.group(1)


def parse_guides(block: str) -> list[dict[str, object]]:
    guides: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    list_key: str | None = None

    for raw_line in block.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = re.match(r"^-\s+name:\s*(.+)$", stripped)
        if match:
            if current is not None:
                guides.append(current)
            current = {"name": strip_quotes(match.group(1))}
            list_key = None
            continue

        if current is None:
            continue

        list_item = re.match(r"^-\s+(.+)$", stripped)
        if list_item and list_key:
            values = current.setdefault(list_key, [])
            assert isinstance(values, list)
            values.append(strip_quotes(list_item.group(1)))
            continue

        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", stripped)
        if not pair:
            continue

        key, raw_value = pair.groups()
        value = strip_quotes(raw_value)
        list_key = None

        if key in {"paths", "exclude", "scopes"}:
            inline = parse_inline_list(raw_value)
            if inline is not None:
                current[key] = inline
            elif raw_value == "":
                current[key] = []
                list_key = key
            else:
                current[key] = [value]
        else:
            current[key] = value

    if current is not None:
        guides.append(current)
    return guides


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    workflow = root / ".beislid" / "workflow.md"
    if not workflow.is_file():
        print(f"{workflow}: missing workflow.md", file=sys.stderr)
        return 1

    text = workflow.read_text(encoding="utf-8")
    block = extract_block(text)
    if not block:
        print(".beislid/workflow.md: missing beislid:guides block", file=sys.stderr)
        return 1

    errors: list[str] = []
    guides = parse_guides(block)
    if not guides:
        errors.append(".beislid/workflow.md: guide registry is empty")

    seen_names: set[str] = set()
    for index, guide in enumerate(guides, start=1):
        name = str(guide.get("name", "")).strip()
        path_value = str(guide.get("path", "")).strip()
        stage = str(guide.get("stage", "")).strip()
        prefix = f"guide #{index}"

        if not name:
            errors.append(f"{prefix}: missing name")
        elif name in seen_names:
            errors.append(f"{prefix}: duplicate guide name `{name}`")
        else:
            seen_names.add(name)

        if not path_value:
            errors.append(f"{prefix}: missing path")
        else:
            path = pathlib.PurePosixPath(path_value)
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"{prefix}: guide path must stay repo-relative: `{path_value}`")
            elif not path_value.endswith(".md"):
                errors.append(f"{prefix}: guide path must end in .md: `{path_value}`")
            elif not (root / path_value).is_file():
                errors.append(f"{prefix}: guide path does not exist: `{path_value}`")

        if not stage:
            errors.append(f"{prefix}: missing stage")
        elif stage not in ALLOWED_STAGES:
            errors.append(f"{prefix}: unsupported stage `{stage}` (expected one of {sorted(ALLOWED_STAGES)})")

        for key in ("paths", "exclude", "scopes"):
            selector = guide.get(key)
            if selector is None:
                continue
            if not isinstance(selector, list) or any(not isinstance(item, str) or not item.strip() for item in selector):
                errors.append(f"{prefix}: `{key}` must be a list of non-empty strings")
            elif key == "paths" and not selector:
                errors.append(f"{prefix}: `paths` cannot be empty when present")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: guide registry validated ({len(guides)} guides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
