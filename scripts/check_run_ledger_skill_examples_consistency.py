#!/usr/bin/env python3
"""Guard run-ledger skill prose from drifting away from the CLI flags.

This is a cheap grep-style check: it validates the required `run-ledger`
examples in skill prose and confirms the run_ledger parser still requires the
same core flags.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


def load_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def parser_block(text: str, command: str) -> str | None:
    match = re.search(
        rf'^\s*\w+_p = sub\.add_parser\("{re.escape(command)}"\)(.*?)(?=^\s*\w+_p = sub\.add_parser\(|\Z)',
        text,
        re.S | re.M,
    )
    return match.group(1) if match else None


def validate_cli(root: pathlib.Path, errors: list[str]) -> None:
    path = root / "scripts" / "run_ledger.py"
    if not path.is_file():
        errors.append("scripts/run_ledger.py: missing required file")
        return

    text = load_text(path)
    blocks = {
        "init": parser_block(text, "init"),
        "checkpoint": parser_block(text, "checkpoint"),
        "gate": parser_block(text, "gate"),
    }
    required_flags = {
        "init": ("--skill",),
        "checkpoint": ("--run-id", "--name"),
        "gate": ("--run-id", "--name"),
    }
    for command, block in blocks.items():
        if block is None:
            errors.append(f"scripts/run_ledger.py: missing {command} parser block")
            continue
        for flag in required_flags[command]:
            if f'add_argument("{flag}"' not in block:
                errors.append(f"scripts/run_ledger.py: {command} parser missing required flag {flag}")


def validate_skill_prose(root: pathlib.Path, errors: list[str]) -> None:
    skills_dir = root / "skills"
    skill_files = sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.exists() else []
    for path in skill_files:
        rel = path.relative_to(root)
        text = load_text(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if "run-ledger" not in line:
                continue
            compact = re.sub(r"\s+", " ", line).strip()
            if re.search(r"beislid run-ledger\s+init\s*/\s*resume", compact):
                errors.append(f"{rel}:{line_no}: split `init/resume` into explicit `init` and/or `resume` commands")
            if "beislid run-ledger init" in compact and "--skill" not in compact:
                errors.append(f"{rel}:{line_no}: init example must include `--skill`")
            if "beislid run-ledger checkpoint" in compact:
                missing = [flag for flag in ("--run-id", "--name") if flag not in compact]
                if missing:
                    joined = ", ".join(missing)
                    errors.append(f"{rel}:{line_no}: checkpoint example missing required flag(s): {joined}")
                if "--step" in compact:
                    errors.append(f"{rel}:{line_no}: checkpoint example must use `--name`, not `--step`")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=pathlib.Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    errors: list[str] = []

    validate_cli(root, errors)
    validate_skill_prose(root, errors)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    skill_count = len(sorted((root / "skills").glob("*/SKILL.md"))) if (root / "skills").exists() else 0
    print(f"ok: run-ledger skill examples are consistent ({skill_count} skill files scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
