#!/usr/bin/env python3
"""Resolve canonical Beislið distribution resources without filesystem search."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


RESOURCE_REGISTRY = {
    "action-policy-protocol": ".beislid/action-policy-protocol.md",
    "artifact-templates": ".beislid/artifact-templates.md",
    "crust-seam-protocol": ".beislid/crust-seam-protocol.md",
    "doctor-templates": ".beislid/doctor-templates.md",
    "envelope-templates": ".beislid/envelope-templates.md",
    "kickoff-templates": ".beislid/kickoff-templates.md",
    "output-templates": ".beislid/output-templates.md",
    "probe-semantics": ".beislid/probe-semantics.md",
    "ready-for-review-templates": ".beislid/ready-for-review-templates.md",
    "review-response-templates": ".beislid/review-response-templates.md",
    "visual-surface-protocol": ".beislid/visual-surface-protocol.md",
    "workflow-md-format": ".beislid/workflow-md-format.md",
}


def resolve_resource(root: Path, name: str) -> Path:
    relative = RESOURCE_REGISTRY.get(name)
    if relative is None:
        known = ", ".join(sorted(RESOURCE_REGISTRY))
        raise ValueError(f"unknown resource name {name!r}; known resources: {known}")

    runtime_root = root.expanduser().resolve()
    candidate = runtime_root / relative
    resolved = candidate.resolve()
    try:
        resolved.relative_to(runtime_root)
    except ValueError as exc:
        raise RuntimeError(f"registered resource escapes runtime root: {name}") from exc

    if not candidate.exists():
        raise RuntimeError(f"registered resource is missing: {candidate}")
    if not candidate.is_file():
        raise RuntimeError(f"registered resource is not a regular file: {candidate}")
    if not os.access(candidate, os.R_OK):
        raise RuntimeError(f"registered resource is not readable: {candidate}")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="validated Beislið runtime root")
    parser.add_argument("name", help="registered logical resource name")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        path = resolve_resource(Path(args.root), args.name)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
