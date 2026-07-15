#!/usr/bin/env python3
"""Create and verify isolated Beislið workspaces."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_ledger


RECEIPT_KIND = "workspace-placement-receipt-v1"
PLACEMENT_OPERATION = "place_mutating_delegate"
CAPABILITY = "verified-manual"
MAX_ALLOCATION_ATTEMPTS = 20
RUNTIME_PROFILE_KIND = "runtime-profile-v1"
RUNTIME_LEASE_KIND = "runtime-lease-v1"
BINDING_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")


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
    if not isinstance(profile, dict) or profile.get("kind") != RUNTIME_PROFILE_KIND:
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
    validate_profile_name(profile_name)
    run = run_ledger.read_json(run_dir / "run.json")
    secrets_root = run_ledger.state_dir() / "secrets"
    path = (
        secrets_root
        / run["repo_hash"]
        / run["run_id"]
        / "workspaces"
        / placement_id
        / profile_name
    )
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
    profile = read_profile(Path(args.profile_file).expanduser().resolve())
    runtime_dir = secure_runtime_dir(run_dir, args.placement_id, profile["name"])
    lease_file = runtime_dir / "lease.json"
    request_file = runtime_dir / "request.json"
    candidate_file = runtime_dir / "candidate.json"
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


def command_probe(args: argparse.Namespace) -> dict[str, Any]:
    try:
        evidence = json.loads(Path(args.evidence_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlacementError(f"host placement evidence is unreadable: {exc}") from exc
    if not isinstance(evidence, dict) or evidence.get("kind") != "host-placement-evidence-v1":
        raise PlacementError("host placement evidence kind must be host-placement-evidence-v1")

    adapter = args.host if args.host in {"codex", "claude", "pi"} else "generic"
    native = evidence.get("native_conformance_passed") is True
    manual = evidence.get("manual_conformance_passed") is True
    acknowledged = evidence.get("destination_acknowledged") is True
    cwd_enforced = evidence.get("cwd_enforced") is True
    runtime = evidence.get("runtime_isolation_verified") is True
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
    elif adapter == "claude" and native and acknowledged and (args.operation == "orchestrator" or runtime):
        capability, disposition, reason_code = "verified-native", "ready", "native_conformance_verified"
    elif manual and cwd_enforced and acknowledged and (args.operation == "orchestrator" or runtime):
        capability, disposition, reason_code = "verified-manual", "ready", "manual_conformance_verified"

    return {
        "kind": "host-placement-probe-v1",
        "host": args.host,
        "host_adapter": adapter,
        "operation": args.operation,
        "capability": capability,
        "disposition": disposition,
        "reason_code": reason_code,
    }


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
    payload = {"cleanup_owner": "beislid", "disposition": "retained", "reason": "cleanup-evidence-required"}
    record_runtime_event(run_dir, args.placement_id, "cleanup_retained", payload)
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

    receipt = {
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
    probe.add_argument("--evidence-file", required=True)

    create = subparsers.add_parser("create", help="create a fresh verified manual worktree")
    create.add_argument("--repo", required=True, help="source Git repository")
    create.add_argument("--expected-sha", required=True, help="full commit SHA for the new worktree")
    create.add_argument("--manual-root", help="repo-sibling or an absolute worktree root")
    create.add_argument("--label", default="placement", help="human-readable placement label")
    create.add_argument("--run-id", required=True, help="initialized external run-ledger id")
    create.add_argument("--flow", required=True, help="run-ledger flow containing the placement receipt")

    preflight = subparsers.add_parser("preflight", help="verify a placement and run configured preparation")
    preflight.add_argument("--repo", required=True)
    preflight.add_argument("--placement-id", required=True)
    preflight.add_argument("--preparation-file")
    preflight.add_argument("--run-id", required=True)
    preflight.add_argument("--flow", required=True)

    lease = subparsers.add_parser("lease", help="allocate and verify an atomic runtime profile")
    lease.add_argument("--repo", required=True)
    lease.add_argument("--placement-id", required=True)
    lease.add_argument("--profile-file", required=True)
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
