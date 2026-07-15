#!/usr/bin/env python3
"""Create and verify isolated Beislið workspaces."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import run_ledger
import workflow_normalizer


RECEIPT_KIND = "workspace-placement-receipt-v1"
PLACEMENT_OPERATIONS = {"ensure_orchestrator_workspace", "place_mutating_delegate"}
MAX_ALLOCATION_ATTEMPTS = 20
RUNTIME_PROFILE_KIND = "runtime-profile-v1"
RUNTIME_LEASE_KIND = "runtime-lease-v1"
BINDING_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
CONFORMANCE_PROOFS = (
    "placement_verified",
    "sha_verified",
    "preparation_verified",
    "runtime_isolation_verified",
    "handoff_verified",
    "integration_verified",
    "cleanup_verified",
)
HOST_PROOF_KIND = "host-placement-proof-v1"
HOST_ADAPTER_BUILD = "workspace-placement-v1"
MAX_PROBE_AGE = timedelta(hours=24)
ATTESTED_ADAPTER_BUILDS: frozenset[str] = frozenset()


class PlacementError(Exception):
    """A placement request failed a user-actionable safety check."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def exclusive_lock(path: Path):
    """Serialize one placement or lease transaction across processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise PlacementError(f"{label} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PlacementError(f"{label} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise PlacementError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


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
    value = os.environ.get("BEISLID_WORKTREE_ROOT") or configured or "repo-sibling"
    if value == "repo-sibling":
        root = repo.parent / f"{repo.name}-worktrees"
    else:
        expanded = Path(value).expanduser()
        if not expanded.is_absolute():
            raise PlacementError("manual root must be 'repo-sibling' or an absolute path")
        root = expanded

    root = root.resolve()
    if value != "repo-sibling":
        ephemeral_roots = {
            Path("/tmp").resolve(),
            Path("/private/tmp").resolve(),
            Path("/var/tmp").resolve(),
            Path("/private/var/folders").resolve(),
        }
        if any(root == ephemeral or ephemeral in root.parents for ephemeral in ephemeral_roots):
            raise PlacementError("manual root must be durable and cannot use a temporary system directory")
    if root == repo or repo in root.parents:
        raise PlacementError("manual root must be outside the source repository")
    return root


def validate_write_scopes(values: list[str]) -> list[str]:
    if not values:
        raise PlacementError("at least one declared write scope is required")
    scopes: list[str] = []
    for value in values:
        normalized = value.replace("\\", "/").strip()
        parts = PurePosixPath(normalized).parts
        if not normalized or normalized.startswith("/") or ".." in parts:
            raise PlacementError(f"write scope must be a repository-relative path pattern: {value}")
        if normalized == ".git" or normalized.startswith(".git/"):
            raise PlacementError("write scope cannot authorize Git metadata")
        if normalized not in scopes:
            scopes.append(normalized)
    return scopes


def scope_regex(pattern: str) -> re.Pattern[str]:
    chunks: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                chunks.append(".*")
                index += 2
                continue
            chunks.append("[^/]*")
        elif character == "?":
            chunks.append("[^/]")
        else:
            chunks.append(re.escape(character))
        index += 1
    chunks.append("$")
    return re.compile("".join(chunks))


def path_in_scope(path: str, scopes: list[str]) -> bool:
    return any(scope_regex(pattern).fullmatch(path) for pattern in scopes)


def literal_scope_prefix(pattern: str) -> str:
    wildcard = min((pattern.find(mark) for mark in ("*", "?") if mark in pattern), default=len(pattern))
    return pattern[:wildcard].rstrip("/")


def scope_patterns_may_overlap(first: str, second: str) -> bool:
    if first == second:
        return True
    first_wild = "*" in first or "?" in first
    second_wild = "*" in second or "?" in second
    if not first_wild and not second_wild:
        return False
    first_prefix = literal_scope_prefix(first)
    second_prefix = literal_scope_prefix(second)
    if not first_prefix or not second_prefix:
        return True
    return first_prefix.startswith(second_prefix) or second_prefix.startswith(first_prefix)


def scopes_may_overlap(first: list[str], second: list[str]) -> bool:
    return any(scope_patterns_may_overlap(left, right) for left in first for right in second)


def active_group_scopes(run_dir: Path, concurrency_group: str) -> list[tuple[str, list[str]]]:
    run = run_ledger.read_json(run_dir / "run.json")
    active: list[tuple[str, list[str]]] = []
    for placement_id, state in run.get("workspaces", {}).items():
        if not isinstance(state, dict) or state.get("last_event") == "cleanup_completed":
            continue
        receipt_path = state.get("receipt")
        if not isinstance(receipt_path, str) or not Path(receipt_path).is_file():
            continue
        receipt = run_ledger.read_json(Path(receipt_path))
        if receipt.get("concurrency_group") != concurrency_group:
            continue
        scope = receipt.get("scope")
        writes = scope.get("write") if isinstance(scope, dict) else None
        if isinstance(writes, list) and all(isinstance(value, str) for value in writes):
            active.append((placement_id, writes))
    return active


def read_evidence(path_value: str, expected_kind: str, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path_value).expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlacementError(f"{label} is unreadable: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("kind") != expected_kind:
        raise PlacementError(f"{label} kind must be {expected_kind}")
    return payload


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


def require_run_ledger(repo: Path, run_id: str, flow: str) -> Path:
    try:
        run_dir = run_ledger.find_run_dir(run_id, repo, flow)
    except SystemExit as exc:
        raise PlacementError(f"automatic placement requires an initialized run ledger: {exc}") from exc
    run = run_ledger.read_json(run_dir / "run.json")
    if run.get("status") != "running":
        raise PlacementError(f"automatic placement requires a running ledger; status is {run.get('status', 'unknown')}")
    return run_dir


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


def require_placement(run_dir: Path, placement_id: str) -> Path:
    try:
        placement_dir = run_ledger.workspace_dir(run_dir, placement_id)
    except SystemExit as exc:
        raise PlacementError(str(exc)) from exc
    if not (placement_dir / "receipt.json").is_file():
        raise PlacementError(f"workspace receipt not found for placement {placement_id}")
    return placement_dir


def placement_workspace(run_dir: Path, placement_id: str) -> Path:
    placement_dir = require_placement(run_dir, placement_id)
    receipt = run_ledger.read_json(placement_dir / "receipt.json")
    workspace = receipt.get("workspace")
    path_value = workspace.get("path") if isinstance(workspace, dict) else None
    if not isinstance(path_value, str):
        raise PlacementError(f"workspace receipt has no destination path for placement {placement_id}")
    path = Path(path_value).resolve()
    if not path.is_dir() or git_root(path) != path:
        raise PlacementError(f"workspace destination is unavailable for placement {placement_id}")
    return path


def validate_profile_name(value: str) -> str:
    if slug(value) != value or "/" in value:
        raise PlacementError("runtime profile name must be a lowercase path-safe segment")
    return value


def read_profile(path: Path) -> dict[str, Any]:
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlacementError(f"runtime profile is unreadable: {exc}") from exc
    if not isinstance(profile, dict):
        raise PlacementError("runtime profile must be a JSON mapping")
    return read_profile_payload(profile)


def read_lease_profile(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    if args.profile_file:
        return read_profile(Path(args.profile_file).expanduser().resolve())
    if not args.workflow_file or not args.profile:
        raise PlacementError("workflow-backed leasing requires --workflow-file and --profile")
    workflow_path = Path(args.workflow_file).expanduser()
    if not workflow_path.is_absolute():
        workflow_path = repo / workflow_path
    envelope = workflow_normalizer.normalize_workflow(workflow_path.resolve())
    if envelope.get("status") != "ok":
        errors = envelope.get("errors") or []
        detail = errors[0].get("message") if errors and isinstance(errors[0], dict) else "workflow is invalid"
        raise PlacementError(f"runtime profile workflow could not be normalized: {detail}")
    isolation = envelope.get("sections", {}).get("agent_isolation")
    profiles = isolation.get("runtime_profiles") if isinstance(isolation, dict) else None
    profile = profiles.get(args.profile) if isinstance(profiles, dict) else None
    if not isinstance(profile, dict):
        raise PlacementError(f"runtime profile not found in workflow: {args.profile}")
    return read_profile_payload({**profile, "kind": RUNTIME_PROFILE_KIND, "name": args.profile})


def read_profile_payload(profile: dict[str, Any]) -> dict[str, Any]:
    if profile.get("kind") != RUNTIME_PROFILE_KIND:
        raise PlacementError(f"runtime profile kind must be {RUNTIME_PROFILE_KIND}")
    name = profile.get("name")
    if not isinstance(name, str):
        raise PlacementError("runtime profile name must be a lowercase path-safe segment")
    validate_profile_name(name)
    required = profile.get("required_bindings")
    if not isinstance(required, list) or not required or any(not isinstance(item, str) for item in required):
        raise PlacementError("runtime profile required_bindings must be a non-empty list")
    if len(set(required)) != len(required) or any(not BINDING_NAME.fullmatch(item) for item in required):
        raise PlacementError("runtime binding names must be unique uppercase environment names")
    provider = profile.get("provider")
    if not isinstance(provider, dict):
        raise PlacementError("runtime profile provider must be a mapping")
    for action in ("allocate", "verify", "release", "reconcile"):
        command = provider.get(action)
        if not isinstance(command, str) or not shlex.split(command):
            raise PlacementError(f"runtime provider {action} command is required")
    return profile


def secure_runtime_dir(run_dir: Path, placement_id: str, profile_name: str) -> Path:
    try:
        placement_id = run_ledger.validate_placement_id(placement_id)
    except SystemExit as exc:
        raise PlacementError(str(exc)) from exc
    validate_profile_name(profile_name)
    run = run_ledger.read_json(run_dir / "run.json")
    secrets_root = run_ledger.state_dir() / "secrets"
    workspace_root = (
        secrets_root
        / run["repo_hash"]
        / run["run_id"]
        / "workspaces"
    ).resolve()
    path = (workspace_root / placement_id / profile_name).resolve()
    if workspace_root not in path.parents:
        raise PlacementError("runtime secret path escaped the run workspace root")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    current = secrets_root
    for segment in path.relative_to(secrets_root).parts:
        current = current / segment
        current.chmod(0o700)
    secrets_root.chmod(0o700)
    return path


def write_secure_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.parent / f".{path.name}.{secrets.token_hex(4)}.tmp"
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def provider_environment(
    action: str,
    request_file: Path,
    lease_file: Path,
    placement_id: str,
    profile_name: str,
) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "BEISLID_RUNTIME_ACTION": action,
            "BEISLID_RUNTIME_REQUEST_FILE": str(request_file),
            "BEISLID_RUNTIME_LEASE_FILE": str(lease_file),
            "BEISLID_PLACEMENT_ID": placement_id,
            "BEISLID_RUNTIME_PROFILE": profile_name,
        }
    )
    return env


def run_provider(
    command: str,
    action: str,
    repo: Path,
    request_file: Path,
    lease_file: Path,
    placement_id: str,
    profile_name: str,
) -> int:
    result = subprocess.run(
        shlex.split(command),
        cwd=repo,
        env=provider_environment(action, request_file, lease_file, placement_id, profile_name),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode


def record_runtime_event(
    run_dir: Path,
    placement_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    try:
        run_ledger.record_workspace_event(run_dir, placement_id, event_type, payload)
    except SystemExit as exc:
        raise PlacementError(f"could not record runtime lifecycle event: {exc}") from exc


def rollback_partial_lease(
    profile: dict[str, Any],
    repo: Path,
    request_file: Path,
    candidate_file: Path,
    placement_id: str,
) -> bool:
    if not candidate_file.is_file():
        return True
    return (
        run_provider(
            profile["provider"]["release"],
            "release",
            repo,
            request_file,
            candidate_file,
            placement_id,
            profile["name"],
        )
        == 0
    )


def command_lease(args: argparse.Namespace) -> dict[str, Any]:
    repo = git_root(Path(args.repo).expanduser().resolve())
    run_dir = require_run_ledger(repo, args.run_id, args.flow)
    workspace = placement_workspace(run_dir, args.placement_id)
    profile = read_lease_profile(args, repo)
    runtime_dir = secure_runtime_dir(run_dir, args.placement_id, profile["name"])
    with exclusive_lock(runtime_dir / ".lease.lock"):
        return command_lease_unlocked(args, repo, run_dir, workspace, profile, runtime_dir)


def command_lease_unlocked(
    args: argparse.Namespace,
    repo: Path,
    run_dir: Path,
    workspace: Path,
    profile: dict[str, Any],
    runtime_dir: Path,
) -> dict[str, Any]:
    lease_file = runtime_dir / "lease.json"
    attempt_id = secrets.token_hex(8)
    request_file = runtime_dir / f"request-{attempt_id}.json"
    candidate_file = runtime_dir / f"candidate-{attempt_id}.json"
    if lease_file.exists():
        existing = run_ledger.read_json(lease_file)
        if existing.get("status") == "active":
            raise PlacementError(f"runtime profile {profile['name']} already has an active lease")

    request = {
        "kind": "runtime-lease-request-v1",
        "run_id": args.run_id,
        "placement_id": args.placement_id,
        "profile": profile["name"],
        "required_bindings": profile["required_bindings"],
    }
    write_secure_json(request_file, request)
    candidate_file.unlink(missing_ok=True)

    allocation_rc = run_provider(
        profile["provider"]["allocate"],
        "allocate",
        workspace,
        request_file,
        candidate_file,
        args.placement_id,
        profile["name"],
    )
    if allocation_rc != 0 or not candidate_file.is_file():
        record_runtime_event(
            run_dir,
            args.placement_id,
            "runtime_lease_failed",
            {"profile": profile["name"], "stage": "allocate", "provider_exit": allocation_rc},
        )
        candidate_file.unlink(missing_ok=True)
        request_file.unlink(missing_ok=True)
        raise PlacementError(f"runtime provider allocation failed with exit {allocation_rc}")

    try:
        candidate = run_ledger.read_json(candidate_file)
    except (OSError, json.JSONDecodeError) as exc:
        rollback_ok = rollback_partial_lease(profile, workspace, request_file, candidate_file, args.placement_id)
        candidate_file.unlink(missing_ok=True)
        request_file.unlink(missing_ok=True)
        record_runtime_event(
            run_dir,
            args.placement_id,
            "runtime_lease_failed",
            {"profile": profile["name"], "stage": "validate", "rollback": rollback_ok},
        )
        raise PlacementError(f"runtime provider returned an unreadable lease: {exc}") from exc

    bindings = candidate.get("bindings")
    if candidate.get("kind") != RUNTIME_LEASE_KIND or not isinstance(candidate.get("lease_id"), str):
        rollback_ok = rollback_partial_lease(profile, workspace, request_file, candidate_file, args.placement_id)
        candidate_file.unlink(missing_ok=True)
        request_file.unlink(missing_ok=True)
        record_runtime_event(
            run_dir,
            args.placement_id,
            "runtime_lease_failed",
            {"profile": profile["name"], "stage": "validate", "rollback": rollback_ok},
        )
        raise PlacementError("runtime provider returned an invalid lease envelope")
    expires_at = candidate.get("expires_at")
    if expires_at is not None:
        try:
            expiry = parse_timestamp(expires_at, "runtime lease expires_at")
            if expiry <= datetime.now(timezone.utc):
                raise PlacementError("runtime lease expires_at must be in the future")
        except PlacementError as exc:
            rollback_ok = rollback_partial_lease(profile, workspace, request_file, candidate_file, args.placement_id)
            candidate_file.unlink(missing_ok=True)
            request_file.unlink(missing_ok=True)
            record_runtime_event(
                run_dir,
                args.placement_id,
                "runtime_lease_failed",
                {"profile": profile["name"], "stage": "expiry", "rollback": rollback_ok},
            )
            raise exc
    if not isinstance(bindings, dict):
        bindings = {}
    missing = sorted(
        name
        for name in profile["required_bindings"]
        if not isinstance(bindings.get(name), str) or not bindings[name]
    )
    if missing:
        rollback_ok = rollback_partial_lease(profile, workspace, request_file, candidate_file, args.placement_id)
        candidate_file.unlink(missing_ok=True)
        request_file.unlink(missing_ok=True)
        record_runtime_event(
            run_dir,
            args.placement_id,
            "runtime_lease_failed",
            {
                "profile": profile["name"],
                "stage": "bindings",
                "missing_bindings": missing,
                "rollback": rollback_ok,
            },
        )
        raise PlacementError(f"missing required runtime bindings: {', '.join(missing)}")

    verification_rc = run_provider(
        profile["provider"]["verify"],
        "verify",
        workspace,
        request_file,
        candidate_file,
        args.placement_id,
        profile["name"],
    )
    if verification_rc != 0:
        rollback_ok = rollback_partial_lease(profile, workspace, request_file, candidate_file, args.placement_id)
        candidate_file.unlink(missing_ok=True)
        request_file.unlink(missing_ok=True)
        record_runtime_event(
            run_dir,
            args.placement_id,
            "runtime_lease_failed",
            {
                "profile": profile["name"],
                "stage": "verify",
                "provider_exit": verification_rc,
                "rollback": rollback_ok,
            },
        )
        raise PlacementError(f"runtime provider verification failed with exit {verification_rc}")

    pepper = secrets.token_bytes(32)
    required_bindings = {name: bindings[name] for name in profile["required_bindings"]}
    fingerprints = {
        name: hmac.new(pepper, f"{name}\0{value}".encode(), hashlib.sha256).hexdigest()
        for name, value in required_bindings.items()
    }
    secret_lease = {
        "kind": "runtime-lease-secret-v1",
        "status": "active",
        "profile": profile["name"],
        "lease_id": candidate["lease_id"],
        "expires_at": candidate.get("expires_at"),
        "required_bindings": profile["required_bindings"],
        "bindings": required_bindings,
        "provider": profile["provider"],
        "fingerprint_key": pepper.hex(),
    }
    write_secure_json(lease_file, secret_lease)
    candidate_file.unlink(missing_ok=True)
    request_file.unlink(missing_ok=True)
    metadata = {
        "profile": profile["name"],
        "lease_id": candidate["lease_id"],
        "expires_at": candidate.get("expires_at"),
        "binding_names": sorted(required_bindings),
        "fingerprints": fingerprints,
    }
    try:
        record_runtime_event(run_dir, args.placement_id, "runtime_leased", metadata)
    except PlacementError:
        rollback_partial_lease(profile, workspace, lease_file, lease_file, args.placement_id)
        lease_file.unlink(missing_ok=True)
        raise
    return metadata


def read_preparation(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        preparation = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlacementError(f"preparation contract is unreadable: {exc}") from exc
    if not isinstance(preparation, dict):
        raise PlacementError("preparation contract must be a mapping")
    command = preparation.get("command")
    if not isinstance(command, str) or not shlex.split(command):
        raise PlacementError("preparation command must be a non-empty string")
    readiness = preparation.get("readiness", [])
    if not isinstance(readiness, list) or any(
        not isinstance(item, str) or not shlex.split(item) for item in readiness
    ):
        raise PlacementError("preparation readiness must be a list of non-empty command strings")
    return {"command": command, "readiness": readiness}


def run_preparation_command(command: str, workspace: Path) -> int:
    return subprocess.run(
        shlex.split(command),
        cwd=workspace,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    ).returncode


def command_preflight(args: argparse.Namespace) -> dict[str, Any]:
    repo = git_root(Path(args.repo).expanduser().resolve())
    run_dir = require_run_ledger(repo, args.run_id, args.flow)
    placement_dir = require_placement(run_dir, args.placement_id)
    workspace = placement_workspace(run_dir, args.placement_id)
    receipt = run_ledger.read_json(placement_dir / "receipt.json")
    expected_sha = receipt.get("repository", {}).get("expected_sha")
    actual_sha = require_git(workspace, "rev-parse", "HEAD", context="preflight SHA check failed")
    status = require_git(workspace, "status", "--porcelain", context="preflight clean-state check failed")
    if actual_sha != expected_sha:
        raise PlacementError(f"preflight SHA mismatch: expected {expected_sha}, got {actual_sha}")
    if status:
        raise PlacementError("preflight destination is not clean")

    preparation = read_preparation(
        Path(args.preparation_file).expanduser().resolve() if args.preparation_file else None
    )
    if preparation is not None:
        rc = run_preparation_command(preparation["command"], workspace)
        if rc != 0:
            record_runtime_event(
                run_dir,
                args.placement_id,
                "preflight_failed",
                {"stage": "preparation", "provider_exit": rc},
            )
            raise PlacementError(f"preparation command failed with exit {rc}")

        tracked_status = require_git(
            workspace,
            "status",
            "--porcelain",
            "--untracked-files=no",
            context="preparation tracked-state check failed",
        )
        prepared_sha = require_git(workspace, "rev-parse", "HEAD", context="preparation SHA check failed")
        if tracked_status or prepared_sha != expected_sha:
            record_runtime_event(
                run_dir,
                args.placement_id,
                "preflight_failed",
                {"stage": "preparation", "tracked_changes": bool(tracked_status), "sha_changed": prepared_sha != expected_sha},
            )
            raise PlacementError("preparation changed tracked files or the expected SHA")

        for index, command in enumerate(preparation["readiness"]):
            rc = run_preparation_command(command, workspace)
            if rc != 0:
                record_runtime_event(
                    run_dir,
                    args.placement_id,
                    "preflight_failed",
                    {"stage": "readiness", "check_index": index, "provider_exit": rc},
                )
                raise PlacementError(f"readiness check {index + 1} failed with exit {rc}")

        final_tracked_status = require_git(
            workspace,
            "status",
            "--porcelain",
            "--untracked-files=no",
            context="readiness tracked-state check failed",
        )
        final_sha = require_git(workspace, "rev-parse", "HEAD", context="readiness SHA check failed")
        if final_tracked_status or final_sha != expected_sha:
            record_runtime_event(
                run_dir,
                args.placement_id,
                "preflight_failed",
                {"stage": "readiness", "tracked_changes": bool(final_tracked_status), "sha_changed": final_sha != expected_sha},
            )
            raise PlacementError("readiness checks changed tracked files or the expected SHA")

    result = {
        "placement_id": args.placement_id,
        "expected_sha": expected_sha,
        "actual_sha": expected_sha,
        "preparation": preparation is not None,
        "readiness_checks": len(preparation["readiness"]) if preparation else 0,
    }
    record_runtime_event(run_dir, args.placement_id, "preflight_passed", result)
    return result


def validate_probe_provenance(
    evidence: dict[str, Any],
    *,
    host: str,
    operation: str,
    repository: Path,
) -> bool:
    if evidence.get("host") != host or evidence.get("operation") != operation:
        return False
    if evidence.get("adapter_build") != HOST_ADAPTER_BUILD:
        return False
    if evidence.get("repository") != str(repository):
        return False
    try:
        generated_at = parse_timestamp(evidence.get("generated_at"), "host evidence generated_at")
        expires_at = parse_timestamp(evidence.get("expires_at"), "host evidence expires_at")
    except PlacementError:
        return False
    current = datetime.now(timezone.utc)
    if generated_at > current + timedelta(minutes=5) or current - generated_at > MAX_PROBE_AGE:
        return False
    if expires_at <= current or expires_at - generated_at > MAX_PROBE_AGE:
        return False
    artifacts = evidence.get("proof_artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(CONFORMANCE_PROOFS):
        return False
    for proof in CONFORMANCE_PROOFS:
        reference = artifacts.get(proof)
        if not isinstance(reference, dict):
            return False
        path_value = reference.get("path")
        digest = reference.get("sha256")
        if not isinstance(path_value, str) or not isinstance(digest, str):
            return False
        path = Path(path_value).expanduser()
        if not path.is_absolute() or not path.is_file():
            return False
        content = path.read_bytes()
        if not hmac.compare_digest(hashlib.sha256(content).hexdigest(), digest):
            return False
        try:
            artifact = json.loads(content)
        except json.JSONDecodeError:
            return False
        expected = {
            "kind": HOST_PROOF_KIND,
            "proof": proof,
            "host": host,
            "operation": operation,
            "adapter_build": HOST_ADAPTER_BUILD,
            "repository": str(repository),
            "passed": True,
        }
        if not isinstance(artifact, dict) or any(artifact.get(key) != value for key, value in expected.items()):
            return False
    return True


def command_probe(args: argparse.Namespace) -> dict[str, Any]:
    evidence = read_evidence(
        args.evidence_file,
        "host-placement-evidence-v1",
        "host placement evidence",
    )

    repository = git_root(Path(args.repo).expanduser().resolve())
    adapter = args.host if args.host in {"codex", "claude", "pi"} else "generic"
    provenance_valid = validate_probe_provenance(
        evidence,
        host=args.host,
        operation=args.operation,
        repository=repository,
    )
    proofs_complete = all(evidence.get(proof) is True for proof in CONFORMANCE_PROOFS)
    complete = (
        proofs_complete
        and provenance_valid
        and HOST_ADAPTER_BUILD in ATTESTED_ADAPTER_BUILDS
    )
    native_claim = evidence.get("native_conformance_passed") is True
    manual_claim = evidence.get("manual_conformance_passed") is True
    native = native_claim and complete
    manual = manual_claim and complete
    acknowledged = evidence.get("destination_acknowledged") is True
    cwd_enforced = evidence.get("cwd_enforced") is True
    capability = "unavailable"
    disposition = "manual-transition-required" if args.operation == "orchestrator" else "sequential"
    reason_code = "manual_path_unverified"

    if adapter == "codex" and args.operation == "orchestrator":
        if native and evidence.get("fork_resolved") is True and acknowledged:
            capability, disposition, reason_code = "verified-native", "ready", "native_conformance_verified"
        elif evidence.get("fork_resolved") is not True:
            reason_code = "codex_fork_unresolved"
        else:
            reason_code = "destination_unacknowledged"
    elif adapter == "pi" and args.operation == "orchestrator":
        if manual and cwd_enforced and evidence.get("relaunch_acknowledged") is True:
            capability, disposition, reason_code = "verified-manual", "ready", "manual_conformance_verified"
        else:
            reason_code = "pi_relaunch_required"
    elif adapter == "claude" and native and acknowledged:
        capability, disposition, reason_code = "verified-native", "ready", "native_conformance_verified"
    elif manual and cwd_enforced and acknowledged:
        capability, disposition, reason_code = "verified-manual", "ready", "manual_conformance_verified"

    if (
        capability == "unavailable"
        and reason_code == "manual_path_unverified"
        and (native_claim or manual_claim)
        and not complete
    ):
        reason_code = (
            "conformance_harness_unavailable"
            if proofs_complete and provenance_valid and HOST_ADAPTER_BUILD not in ATTESTED_ADAPTER_BUILDS
            else "conformance_evidence_incomplete"
        )

    return {
        "kind": "host-placement-probe-v1",
        "host": args.host,
        "host_adapter": adapter,
        "operation": args.operation,
        "capability": capability,
        "disposition": disposition,
        "reason_code": reason_code,
    }


def require_string_list(
    payload: dict[str, Any],
    key: str,
    label: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    values = payload.get(key)
    if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
        raise PlacementError(f"{label} must be a list of non-empty strings")
    if not allow_empty and not values:
        raise PlacementError(f"{label} must not be empty")
    if len(values) != len(set(values)):
        raise PlacementError(f"{label} must not contain duplicates")
    return values


def command_validate_handoff(args: argparse.Namespace) -> dict[str, Any]:
    repo = git_root(Path(args.repo).expanduser().resolve())
    run_dir = require_run_ledger(repo, args.run_id, args.flow)
    placement_dir = require_placement(run_dir, args.placement_id)
    receipt = run_ledger.read_json(placement_dir / "receipt.json")
    workspace = placement_workspace(run_dir, args.placement_id)
    handoff = read_evidence(args.handoff_file, "workspace-handoff-v1", "workspace handoff")

    repository = receipt.get("repository")
    scope = receipt.get("scope")
    if not isinstance(repository, dict) or not isinstance(scope, dict):
        raise PlacementError("workspace receipt lacks repository or write-scope evidence")
    expected_base = repository.get("expected_sha")
    if handoff.get("expected_base_sha") != expected_base:
        raise PlacementError("handoff expected base SHA does not match the placement receipt")
    scopes = scope.get("write")
    if not isinstance(scopes, list) or any(not isinstance(scope, str) for scope in scopes):
        raise PlacementError("workspace receipt lacks a valid declared write scope")

    status = require_git(workspace, "status", "--porcelain", context="handoff clean-state check failed")
    if status:
        raise PlacementError("handoff workspace must be clean, including untracked files")
    final_head = require_git(workspace, "rev-parse", "HEAD", context="handoff HEAD check failed")
    if run_git(workspace, "merge-base", "--is-ancestor", str(expected_base), final_head).returncode != 0:
        raise PlacementError("handoff expected base is not an ancestor of final HEAD")
    final_commits = require_string_list(handoff, "final_commits", "handoff final_commits")
    for commit in final_commits:
        resolved = require_git(
            workspace,
            "rev-parse",
            "--verify",
            f"{commit}^{{commit}}",
            context=f"handoff commit does not exist: {commit}",
        )
        if resolved != commit:
            raise PlacementError(f"handoff commit must be a full canonical SHA: {commit}")
        if run_git(workspace, "merge-base", "--is-ancestor", commit, final_head).returncode != 0:
            raise PlacementError(f"handoff commit is not reachable from final HEAD: {commit}")
    if final_commits[-1] != final_head:
        raise PlacementError("handoff final commit does not match workspace HEAD")

    actual_commits_output = require_git(
        workspace,
        "rev-list",
        "--reverse",
        f"{expected_base}..{final_head}",
        context="handoff commit range check failed",
    )
    actual_commits = actual_commits_output.splitlines() if actual_commits_output else []
    if final_commits != actual_commits:
        raise PlacementError("handoff final_commits must exactly describe the placement commit range")

    changed_output = require_git(
        workspace,
        "diff",
        "--no-renames",
        "--name-only",
        "--diff-filter=ACDMRTUXB",
        f"{expected_base}..{final_head}",
        context="handoff changed-path check failed",
    )
    actual_paths = sorted(changed_output.splitlines()) if changed_output else []
    reported_paths = sorted(require_string_list(handoff, "changed_paths", "handoff changed_paths"))
    if reported_paths != actual_paths:
        raise PlacementError("handoff changed_paths must exactly match the committed diff")
    escaped = [path for path in actual_paths if not path_in_scope(path, scopes)]
    if escaped:
        raise PlacementError(f"handoff contains paths outside the declared write scope: {', '.join(escaped)}")

    require_string_list(handoff, "verification", "handoff verification")
    cleanup_disposition = handoff.get("cleanup_disposition")
    if cleanup_disposition != "beislid-after-integration":
        raise PlacementError("manual handoff cleanup_disposition must be beislid-after-integration")
    result = {
        "placement_id": args.placement_id,
        "expected_base_sha": expected_base,
        "final_head": final_head,
        "final_commits": final_commits,
        "changed_paths": actual_paths,
        "write_scope": scopes,
        "cleanup_disposition": cleanup_disposition,
    }
    record_runtime_event(run_dir, args.placement_id, "handoff_validated", result)
    return result


def runtime_leases_released(run_dir: Path, placement_id: str) -> bool:
    run = run_ledger.read_json(run_dir / "run.json")
    workspace_runtime_root = (
        run_ledger.state_dir()
        / "secrets"
        / run["repo_hash"]
        / run["run_id"]
        / "workspaces"
        / placement_id
    )
    if not workspace_runtime_root.is_dir():
        return True
    leases = list(workspace_runtime_root.glob("*/lease.json"))
    return all(run_ledger.read_json(lease).get("status") == "released" for lease in leases)


def commit_patch_id(repo: Path, commit: str) -> str:
    patch = run_git(repo, "show", "--pretty=format:", "--binary", "--no-ext-diff", commit)
    if patch.returncode != 0:
        raise PlacementError(f"could not inspect integration patch for commit {commit}")
    result = subprocess.run(
        ["git", "patch-id", "--stable"],
        cwd=repo,
        input=patch.stdout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise PlacementError(f"could not derive integration patch identity for commit {commit}")
    return result.stdout.split()[0]


def command_cleanup(args: argparse.Namespace) -> dict[str, Any]:
    repo = git_root(Path(args.repo).expanduser().resolve())
    run_dir = require_run_ledger(repo, args.run_id, args.flow)
    placement_dir = require_placement(run_dir, args.placement_id)
    receipt = run_ledger.read_json(placement_dir / "receipt.json")
    workspace = receipt.get("workspace")
    owner = workspace.get("cleanup_owner") if isinstance(workspace, dict) else None
    if owner == "host":
        payload = {"cleanup_owner": "host", "disposition": "host-cleanup-required"}
        record_runtime_event(run_dir, args.placement_id, "cleanup_deferred", payload)
        return payload
    if owner == "user" or owner not in {"host", "beislid"}:
        payload = {"cleanup_owner": "user", "disposition": "user-cleanup-required"}
        record_runtime_event(run_dir, args.placement_id, "cleanup_deferred", payload)
        return payload

    if not args.evidence_file:
        raise PlacementError("Beislid-owned cleanup requires an evidence file")
    evidence = read_evidence(
        args.evidence_file,
        "workspace-cleanup-evidence-v1",
        "workspace cleanup evidence",
    )
    policy = evidence.get("action_policy")
    policy_fields = {
        "decision",
        "mode",
        "action",
        "classes",
        "matched_rules",
        "sandbox_status",
        "requires_human",
        "log_level",
        "reason",
        "remediation",
    }
    if not isinstance(policy, dict) or not policy_fields.issubset(policy):
        raise PlacementError("cleanup evidence requires a complete action-policy envelope")
    if policy.get("action") != "agent.workspace.cleanup":
        raise PlacementError("cleanup action-policy envelope is for the wrong action")
    if policy.get("decision") != "allow" or policy.get("requires_human") is not False:
        raise PlacementError("cleanup action policy did not allow deletion")
    require_string_list(evidence, "verification", "cleanup verification")
    if evidence.get("runtime_profiles_released") is not True:
        raise PlacementError("cleanup evidence must confirm runtime profile release")
    if not runtime_leases_released(run_dir, args.placement_id):
        raise PlacementError("one or more runtime profile leases remain active")

    workspace_path = Path(workspace.get("path", "")).resolve() if isinstance(workspace, dict) else Path()
    branch = workspace.get("branch") if isinstance(workspace, dict) else None
    if not workspace_path.is_dir() or not isinstance(branch, str) or not branch:
        raise PlacementError("workspace receipt lacks a live path or branch for cleanup")
    listing = require_git(repo, "worktree", "list", "--porcelain", context="worktree registration check failed")
    if f"worktree {workspace_path}" not in listing.splitlines():
        raise PlacementError("cleanup target is not a registered worktree of the source repository")
    actual_branch = require_git(
        workspace_path,
        "branch",
        "--show-current",
        context="cleanup branch check failed",
    )
    if actual_branch != branch:
        raise PlacementError(f"cleanup branch mismatch: expected {branch}, got {actual_branch}")
    status = require_git(workspace_path, "status", "--porcelain", context="cleanup clean-state check failed")
    if status:
        raise PlacementError("cleanup target must be clean, including untracked files")
    workspace_head = require_git(workspace_path, "rev-parse", "HEAD", context="cleanup HEAD check failed")
    integration_map = evidence.get("integration_map")
    if not isinstance(integration_map, list) or not integration_map:
        raise PlacementError("cleanup integration_map must be a non-empty list")
    expected_base = receipt.get("repository", {}).get("expected_sha")
    if not isinstance(expected_base, str):
        raise PlacementError("workspace receipt lacks the expected base SHA")
    source_output = require_git(
        workspace_path,
        "rev-list",
        "--reverse",
        f"{expected_base}..{workspace_head}",
        context="workspace integration range check failed",
    )
    source_commits = source_output.splitlines() if source_output else []
    if not source_commits:
        raise PlacementError("cleanup requires at least one committed workspace change")
    mapped_sources: list[str] = []
    integration_head = require_git(repo, "rev-parse", "HEAD", context="integration HEAD check failed")
    for mapping in integration_map:
        if not isinstance(mapping, dict):
            raise PlacementError("cleanup integration_map entries must be mappings")
        source_commit = mapping.get("source_commit")
        integrated_commit = mapping.get("integrated_commit")
        if not isinstance(source_commit, str) or not isinstance(integrated_commit, str):
            raise PlacementError("cleanup integration_map entries require source_commit and integrated_commit")
        mapped_sources.append(source_commit)
        resolved = require_git(
            repo,
            "rev-parse",
            "--verify",
            f"{integrated_commit}^{{commit}}",
            context=f"integrated commit does not exist: {integrated_commit}",
        )
        if resolved != integrated_commit:
            raise PlacementError(f"integrated commit must be a full canonical SHA: {integrated_commit}")
        if run_git(repo, "merge-base", "--is-ancestor", integrated_commit, integration_head).returncode != 0:
            raise PlacementError(f"integrated commit is not reachable from the integration branch: {integrated_commit}")
        if commit_patch_id(repo, source_commit) != commit_patch_id(repo, integrated_commit):
            raise PlacementError(
                f"integrated commit patch does not match source commit: {source_commit} -> {integrated_commit}"
            )
    if mapped_sources != source_commits:
        raise PlacementError("cleanup integration_map must exactly cover the workspace commit range")

    authorized = {
        "cleanup_owner": "beislid",
        "workspace_head": workspace_head,
        "integration_head": integration_head,
        "integration_map": integration_map,
        "branch": branch,
    }
    record_runtime_event(run_dir, args.placement_id, "cleanup_authorized", authorized)
    removed = run_git(repo, "worktree", "remove", str(workspace_path))
    if removed.returncode != 0:
        detail = removed.stderr.strip() or removed.stdout.strip() or "git worktree remove failed"
        raise PlacementError(f"automatic cleanup failed: {detail}")
    deleted = run_git(repo, "branch", "-D", branch)
    if deleted.returncode != 0:
        detail = deleted.stderr.strip() or deleted.stdout.strip() or "git branch deletion failed"
        raise PlacementError(f"workspace was removed but cleanup branch remains: {detail}")
    payload = {
        "cleanup_owner": "beislid",
        "disposition": "cleaned",
        "workspace_head": workspace_head,
        "integration_head": integration_head,
        "branch_deleted": branch,
    }
    record_runtime_event(run_dir, args.placement_id, "cleanup_completed", payload)
    return payload


def runtime_lease_for(args: argparse.Namespace) -> tuple[Path, Path, dict[str, Any]]:
    repo = git_root(Path(args.repo).expanduser().resolve())
    run_dir = require_run_ledger(repo, args.run_id, args.flow)
    workspace = placement_workspace(run_dir, args.placement_id)
    runtime_dir = secure_runtime_dir(run_dir, args.placement_id, args.profile)
    lease_file = runtime_dir / "lease.json"
    if not lease_file.is_file():
        raise PlacementError(f"runtime lease not found for profile {args.profile}")
    return workspace, run_dir, run_ledger.read_json(lease_file)


def command_runtime_exec(args: argparse.Namespace) -> int:
    workspace, _, lease = runtime_lease_for(args)
    if lease.get("status") != "active":
        raise PlacementError(f"runtime lease is not active for profile {args.profile}")
    expires_at = lease.get("expires_at")
    if expires_at is not None and parse_timestamp(expires_at, "runtime lease expires_at") <= datetime.now(timezone.utc):
        raise PlacementError(f"runtime lease is expired for profile {args.profile}; reconcile or allocate a new lease")
    command = list(args.exec_command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise PlacementError("workspace exec requires a command after --")
    env = os.environ.copy()
    env.update(lease["bindings"])
    env["BEISLID_PLACEMENT_ID"] = args.placement_id
    env["BEISLID_RUNTIME_PROFILE"] = args.profile
    env["BEISLID_RUNTIME_LEASE_ID"] = lease["lease_id"]
    return subprocess.run(command, cwd=workspace, env=env, check=False).returncode


def command_reconcile(args: argparse.Namespace) -> dict[str, Any]:
    workspace, run_dir, lease = runtime_lease_for(args)
    if lease.get("status") != "active":
        raise PlacementError(f"runtime lease is not active for profile {args.profile}")
    runtime_dir = secure_runtime_dir(run_dir, args.placement_id, args.profile)
    lease_file = runtime_dir / "lease.json"
    request_file = runtime_dir / "reconcile-request.json"
    write_secure_json(request_file, {"placement_id": args.placement_id, "profile": args.profile})
    rc = run_provider(
        lease["provider"]["reconcile"],
        "reconcile",
        workspace,
        request_file,
        lease_file,
        args.placement_id,
        args.profile,
    )
    request_file.unlink(missing_ok=True)
    if rc != 0:
        raise PlacementError(f"runtime provider reconciliation failed with exit {rc}")
    payload = {"profile": args.profile, "lease_id": lease["lease_id"], "status": "confirmed"}
    record_runtime_event(run_dir, args.placement_id, "runtime_reconciled", payload)
    return payload


def command_release(args: argparse.Namespace) -> dict[str, Any]:
    workspace, run_dir, lease = runtime_lease_for(args)
    if lease.get("status") == "released":
        return {"profile": args.profile, "lease_id": lease["lease_id"], "already_released": True}
    if lease.get("status") != "active":
        raise PlacementError(f"runtime lease has unknown status for profile {args.profile}")
    runtime_dir = secure_runtime_dir(run_dir, args.placement_id, args.profile)
    lease_file = runtime_dir / "lease.json"
    request_file = runtime_dir / "release-request.json"
    write_secure_json(request_file, {"placement_id": args.placement_id, "profile": args.profile})
    rc = run_provider(
        lease["provider"]["release"],
        "release",
        workspace,
        request_file,
        lease_file,
        args.placement_id,
        args.profile,
    )
    request_file.unlink(missing_ok=True)
    if rc != 0:
        raise PlacementError(f"runtime provider release failed with exit {rc}")
    released_at = now()
    released = {
        "kind": "runtime-lease-secret-v1",
        "status": "released",
        "profile": args.profile,
        "lease_id": lease["lease_id"],
        "released_at": released_at,
    }
    write_secure_json(lease_file, released)
    payload = {
        "profile": args.profile,
        "lease_id": lease["lease_id"],
        "released_at": released_at,
        "already_released": False,
    }
    record_runtime_event(run_dir, args.placement_id, "runtime_released", payload)
    return payload


def create_manual_placement(args: argparse.Namespace) -> dict[str, Any]:
    repo = git_root(Path(args.repo).expanduser().resolve())
    run_dir = require_run_ledger(repo, args.run_id, args.flow)
    with exclusive_lock(run_dir / ".workspace-placement.lock"):
        return create_manual_placement_locked(args)


def create_manual_placement_locked(args: argparse.Namespace) -> dict[str, Any]:
    repo = git_root(Path(args.repo).expanduser().resolve())
    run_dir = require_run_ledger(repo, args.run_id, args.flow)
    expected_sha = require_source_preflight(repo, args.expected_sha)
    write_scopes = validate_write_scopes(args.write_scope)
    concurrency_group = args.concurrency_group
    if concurrency_group is not None:
        if slug(concurrency_group) != concurrency_group:
            raise PlacementError("concurrency group must be a lowercase path-safe segment")
        for placement_id, active_scopes in active_group_scopes(run_dir, concurrency_group):
            if scopes_may_overlap(write_scopes, active_scopes):
                raise PlacementError(
                    f"write scope may overlap active placement {placement_id} in concurrency group {concurrency_group}"
                )
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

    receipt = {
        "kind": RECEIPT_KIND,
        "placement_id": placement_id,
        "operation": args.operation,
        "capability": "unavailable",
        "placement_status": "verified",
        "concurrency_group": concurrency_group,
        "created_at": now(),
        "repository": {
            "source": str(repo),
            "expected_sha": expected_sha,
            "actual_sha": actual_sha,
        },
        "scope": {
            "write": write_scopes,
        },
        "workspace": {
            "path": str(path.resolve()),
            "branch": branch,
            "clean": True,
            "cleanup_owner": "beislid",
            "created_by": "beislid",
        },
    }
    try:
        _, stored_receipt = run_ledger.record_workspace_receipt(run_dir, receipt)
    except SystemExit as exc:
        raise PlacementError(
            f"ledger receipt failed after creating retained workspace {path.resolve()}: {exc}"
        ) from exc
    return stored_receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    probe = subparsers.add_parser("probe", help="evaluate evidence-backed host placement capability")
    probe.add_argument("--host", required=True)
    probe.add_argument("--operation", required=True, choices=("orchestrator", "delegate"))
    probe.add_argument("--repo", required=True, help="repository the evidence must be bound to")
    probe.add_argument("--evidence-file", required=True)

    create = subparsers.add_parser("create", help="create a fresh verified manual worktree")
    create.add_argument("--repo", required=True, help="source Git repository")
    create.add_argument("--operation", required=True, choices=sorted(PLACEMENT_OPERATIONS))
    create.add_argument("--expected-sha", required=True, help="full commit SHA for the new worktree")
    create.add_argument("--manual-root", help="repo-sibling or an absolute worktree root")
    create.add_argument("--label", default="placement", help="human-readable placement label")
    create.add_argument(
        "--concurrency-group",
        help="shared path-safe batch id whose active placements must have disjoint write scopes",
    )
    create.add_argument(
        "--write-scope",
        action="append",
        required=True,
        help="repository-relative authorized path pattern; repeat for multiple scopes",
    )
    create.add_argument("--run-id", required=True, help="initialized external run-ledger id")
    create.add_argument("--flow", required=True, help="run-ledger flow containing the placement receipt")

    preflight = subparsers.add_parser("preflight", help="verify a placement and run configured preparation")
    preflight.add_argument("--repo", required=True)
    preflight.add_argument("--placement-id", required=True)
    preflight.add_argument("--preparation-file")
    preflight.add_argument("--run-id", required=True)
    preflight.add_argument("--flow", required=True)

    handoff = subparsers.add_parser("validate-handoff", help="validate a committed delegate handoff")
    handoff.add_argument("--repo", required=True)
    handoff.add_argument("--placement-id", required=True)
    handoff.add_argument("--handoff-file", required=True)
    handoff.add_argument("--run-id", required=True)
    handoff.add_argument("--flow", required=True)

    lease = subparsers.add_parser("lease", help="allocate and verify an atomic runtime profile")
    lease.add_argument("--repo", required=True)
    lease.add_argument("--placement-id", required=True)
    profile_source = lease.add_mutually_exclusive_group(required=True)
    profile_source.add_argument("--profile-file")
    profile_source.add_argument("--workflow-file")
    lease.add_argument("--profile", help="runtime profile name when --workflow-file is used")
    lease.add_argument("--run-id", required=True)
    lease.add_argument("--flow", required=True)

    runtime_exec = subparsers.add_parser("exec", help="run a command with active runtime bindings")
    runtime_exec.add_argument("--repo", required=True)
    runtime_exec.add_argument("--placement-id", required=True)
    runtime_exec.add_argument("--profile", required=True)
    runtime_exec.add_argument("--run-id", required=True)
    runtime_exec.add_argument("--flow", required=True)
    runtime_exec.add_argument("exec_command", nargs=argparse.REMAINDER)

    reconcile = subparsers.add_parser("reconcile", help="ask the provider to reconcile an active lease")
    reconcile.add_argument("--repo", required=True)
    reconcile.add_argument("--placement-id", required=True)
    reconcile.add_argument("--profile", required=True)
    reconcile.add_argument("--run-id", required=True)
    reconcile.add_argument("--flow", required=True)

    release = subparsers.add_parser("release", help="idempotently release an active runtime lease")
    release.add_argument("--repo", required=True)
    release.add_argument("--placement-id", required=True)
    release.add_argument("--profile", required=True)
    release.add_argument("--run-id", required=True)
    release.add_argument("--flow", required=True)

    cleanup = subparsers.add_parser("cleanup", help="route cleanup through the recorded ownership boundary")
    cleanup.add_argument("--repo", required=True)
    cleanup.add_argument("--placement-id", required=True)
    cleanup.add_argument("--evidence-file")
    cleanup.add_argument("--run-id", required=True)
    cleanup.add_argument("--flow", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "probe":
            payload = command_probe(args)
        elif args.command == "create":
            payload = create_manual_placement(args)
        elif args.command == "preflight":
            payload = command_preflight(args)
        elif args.command == "validate-handoff":
            payload = command_validate_handoff(args)
        elif args.command == "lease":
            payload = command_lease(args)
        elif args.command == "exec":
            return command_runtime_exec(args)
        elif args.command == "reconcile":
            payload = command_reconcile(args)
        elif args.command == "release":
            payload = command_release(args)
        elif args.command == "cleanup":
            payload = command_cleanup(args)
        else:
            raise PlacementError(f"unsupported command: {args.command}")
    except PlacementError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
