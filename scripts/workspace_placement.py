#!/usr/bin/env python3
"""Create and verify isolated Beislið workspaces."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RECEIPT_KIND = "workspace-placement-receipt-v1"
PLACEMENT_OPERATION = "place_mutating_delegate"
CAPABILITY = "verified-manual"
MAX_ALLOCATION_ATTEMPTS = 20


class PlacementError(Exception):
    """A placement request failed a user-actionable safety check."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require_git(repo: Path, *args: str, context: str) -> str:
    result = run_git(repo, *args)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise PlacementError(f"{context}: {detail}")
    return result.stdout.strip()


def git_root(repo: Path) -> Path:
    if not repo.is_dir():
        raise PlacementError(f"repository does not exist: {repo}")
    root = require_git(repo, "rev-parse", "--show-toplevel", context="repository validation failed")
    return Path(root).resolve()


def slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._").lower()
    return normalized or "placement"


def resolve_manual_root(repo: Path, configured: str | None) -> Path:
    value = configured or os.environ.get("BEISLID_WORKTREE_ROOT") or "repo-sibling"
    if value == "repo-sibling":
        root = repo.parent / f"{repo.name}-worktrees"
    else:
        expanded = Path(value).expanduser()
        if not expanded.is_absolute():
            raise PlacementError("manual root must be 'repo-sibling' or an absolute path")
        root = expanded

    root = root.resolve()
    if root == repo or repo in root.parents:
        raise PlacementError("manual root must be outside the source repository")
    return root


def require_source_preflight(repo: Path, expected_sha: str) -> str:
    resolved = run_git(repo, "rev-parse", "--verify", f"{expected_sha}^{{commit}}")
    if resolved.returncode != 0:
        raise PlacementError(f"expected SHA is not a commit in the source repository: {expected_sha}")
    actual = resolved.stdout.strip()
    if actual != expected_sha:
        raise PlacementError(f"expected SHA must be the full canonical commit SHA: {expected_sha}")

    tracked_status = require_git(
        repo,
        "status",
        "--porcelain",
        "--untracked-files=no",
        context="source clean-state check failed",
    )
    if tracked_status:
        raise PlacementError("source repository has tracked changes; commit or preserve them before placement")
    return actual


def allocate_identity(repo: Path, root: Path, label: str) -> tuple[str, str, Path]:
    prefix = slug(label)
    for _ in range(MAX_ALLOCATION_ATTEMPTS):
        placement_id = f"{prefix}-{secrets.token_hex(6)}"
        branch = f"beislid/placement/{placement_id}"
        path = root / placement_id
        branch_exists = run_git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0
        if not path.exists() and not branch_exists:
            return placement_id, branch, path
    raise PlacementError("could not allocate a unique placement path and branch")


def remove_failed_worktree(repo: Path, path: Path, branch: str) -> None:
    if path.exists():
        run_git(repo, "worktree", "remove", "--force", str(path))
    run_git(repo, "branch", "-D", branch)


def create_manual_placement(args: argparse.Namespace) -> dict[str, Any]:
    repo = git_root(Path(args.repo).expanduser().resolve())
    expected_sha = require_source_preflight(repo, args.expected_sha)
    root = resolve_manual_root(repo, args.manual_root)
    placement_id, branch, path = allocate_identity(repo, root, args.label)
    root.mkdir(parents=True, exist_ok=True)

    created = run_git(repo, "worktree", "add", "-b", branch, str(path), expected_sha)
    if created.returncode != 0:
        remove_failed_worktree(repo, path, branch)
        detail = created.stderr.strip() or created.stdout.strip() or "git worktree add failed"
        raise PlacementError(f"manual worktree creation failed: {detail}")

    try:
        actual_sha = require_git(path, "rev-parse", "HEAD", context="destination SHA check failed")
        actual_root = Path(
            require_git(path, "rev-parse", "--show-toplevel", context="destination root check failed")
        ).resolve()
        actual_branch = require_git(path, "branch", "--show-current", context="destination branch check failed")
        status = require_git(path, "status", "--porcelain", context="destination clean-state check failed")
        if actual_sha != expected_sha:
            raise PlacementError(f"destination SHA mismatch: expected {expected_sha}, got {actual_sha}")
        if actual_root != path.resolve():
            raise PlacementError(f"destination root mismatch: expected {path.resolve()}, got {actual_root}")
        if actual_branch != branch:
            raise PlacementError(f"destination branch mismatch: expected {branch}, got {actual_branch}")
        if status:
            raise PlacementError("destination worktree is not clean after creation")
    except PlacementError:
        remove_failed_worktree(repo, path, branch)
        raise

    return {
        "kind": RECEIPT_KIND,
        "placement_id": placement_id,
        "operation": PLACEMENT_OPERATION,
        "capability": CAPABILITY,
        "created_at": now(),
        "repository": {
            "source": str(repo),
            "expected_sha": expected_sha,
            "actual_sha": actual_sha,
        },
        "workspace": {
            "path": str(path.resolve()),
            "branch": branch,
            "clean": True,
            "cleanup_owner": "beislid",
            "created_by": "beislid",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="create a fresh verified manual worktree")
    create.add_argument("--repo", required=True, help="source Git repository")
    create.add_argument("--expected-sha", required=True, help="full commit SHA for the new worktree")
    create.add_argument("--manual-root", help="repo-sibling or an absolute worktree root")
    create.add_argument("--label", default="placement", help="human-readable placement label")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "create":
            receipt = create_manual_placement(args)
        else:
            raise PlacementError(f"unsupported command: {args.command}")
    except PlacementError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
