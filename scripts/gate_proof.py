#!/usr/bin/env python3
"""Exact, content-addressed reuse decisions for deterministic gate evidence."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import re
import secrets
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


REQUEST_KIND = "gate-proof-request-v1"
IDENTITY_KIND = "gate-proof-identity-v1"
PROOF_KIND = "gate-proof-v1"
DECISION_KIND = "gate-proof-decision-v1"
RECORD_KIND = "gate-proof-record-v1"
RUN_ID_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ProofUnavailable(Exception):
    """A safe fail-closed reason that requires normal gate execution."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def state_dir() -> Path:
    return Path(os.environ.get("BEISLID_STATE_DIR", Path.home() / ".local" / "state" / "beislid")).resolve()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProofUnavailable("request_invalid", f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{secrets.token_hex(4)}.tmp"
    try:
        with temporary.open("w", encoding="utf-8") as target:
            json.dump(payload, target, indent=2, sort_keys=True)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def command_output(argv: list[str], cwd: Path) -> str:
    result = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ProofUnavailable("identity_probe_failed", f"command failed while computing proof identity: {argv[0]}")
    return result.stdout.strip()


def git_output(repo: Path, *args: str) -> str:
    return command_output(["git", *args], repo)


def repo_root(cwd: Path | None = None) -> Path:
    start = cwd or Path.cwd()
    root = command_output(["git", "rev-parse", "--show-toplevel"], start)
    return Path(root).resolve()


def relative_cwd(repo: Path, value: object) -> tuple[str, Path]:
    if not isinstance(value, str) or not value.strip():
        raise ProofUnavailable("request_invalid", "gate.cwd must be a non-empty string")
    candidate = (repo / value).resolve()
    try:
        relative = candidate.relative_to(repo)
    except ValueError as exc:
        raise ProofUnavailable("request_invalid", "gate.cwd must stay inside the repository") from exc
    if not candidate.is_dir():
        raise ProofUnavailable("request_invalid", "gate.cwd must resolve to a directory")
    normalized = "." if relative == Path(".") else relative.as_posix()
    return normalized, candidate


def required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProofUnavailable("request_invalid", f"{key} must be a non-empty string")
    return value


def environment_fingerprint(config: object, cwd: Path) -> str:
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise ProofUnavailable("request_invalid", "evidence_reuse.environment must be an object")

    variables = config.get("variables", [])
    commands = config.get("commands", [])
    if not isinstance(variables, list) or not all(isinstance(item, str) and item for item in variables):
        raise ProofUnavailable("request_invalid", "environment.variables must contain non-empty strings")
    if not isinstance(commands, list):
        raise ProofUnavailable("request_invalid", "environment.commands must be a list")

    variable_values = []
    for name in sorted(set(variables)):
        value = os.environ.get(name)
        variable_values.append(
            {
                "name_sha256": sha256_bytes(name.encode("utf-8")),
                "state": "unset" if value is None else "set",
                "value_sha256": None if value is None else sha256_bytes(value.encode("utf-8")),
            }
        )

    command_values = []
    for raw_argv in commands:
        if not isinstance(raw_argv, list) or not raw_argv or not all(isinstance(item, str) and item for item in raw_argv):
            raise ProofUnavailable("request_invalid", "environment.commands entries must be non-empty argv lists")
        result = subprocess.run(
            raw_argv,
            cwd=cwd,
            text=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0:
            raise ProofUnavailable("environment_probe_failed", f"environment fingerprint command failed: {raw_argv[0]}")
        command_values.append(
            {
                "argv_sha256": sha256_bytes(canonical_json(raw_argv)),
                "output_sha256": sha256_bytes(result.stdout),
            }
        )

    fingerprint = {
        "commands": command_values,
        "host": {
            "machine": platform.machine(),
            "os": os.name,
            "system": platform.system(),
        },
        "variables": variable_values,
    }
    return sha256_bytes(canonical_json(fingerprint))


def compute_identity(request: dict[str, Any], repo: Path) -> tuple[dict[str, Any], str, dict[str, str]]:
    if request.get("kind") != REQUEST_KIND:
        raise ProofUnavailable("request_invalid", f"request kind must be {REQUEST_KIND}")
    gate = request.get("gate")
    selection = request.get("selection")
    if not isinstance(gate, dict) or not isinstance(selection, dict):
        raise ProofUnavailable("request_invalid", "request requires gate and selection objects")

    evidence = gate.get("evidence_reuse")
    if not isinstance(evidence, dict) or evidence.get("mode") != "exact":
        raise ProofUnavailable("reuse_not_enabled", "gate does not opt into exact evidence reuse")
    if gate.get("mutates") is not False:
        raise ProofUnavailable("gate_mutates", "mutating gates cannot reuse evidence")

    name = required_string(gate, "name")
    command = required_string(gate, "command")
    scope = gate.get("scope", "repo")
    if not isinstance(scope, str) or not scope:
        raise ProofUnavailable("request_invalid", "gate.scope must be a non-empty string")
    normalized_cwd, gate_cwd = relative_cwd(repo, gate.get("cwd", "."))

    dirty = git_output(repo, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise ProofUnavailable("dirty_worktree", "exact gate evidence requires a clean worktree")

    workflow_path = repo / ".beislid" / "workflow.md"
    if not workflow_path.is_file():
        raise ProofUnavailable("workflow_missing", "exact gate evidence requires .beislid/workflow.md")

    base = required_string(selection, "base")
    base_commit = git_output(repo, "rev-parse", "--verify", f"{base}^{{commit}}")
    changed_output = subprocess.run(
        ["git", "diff", "--name-only", "-z", "--no-renames", f"{base_commit}...HEAD"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if changed_output.returncode != 0:
        raise ProofUnavailable("selection_failed", "could not compute changed files for gate evidence")
    changed_files = sorted(item.decode("utf-8", errors="surrogateescape") for item in changed_output.stdout.split(b"\0") if item)

    roots = sorted(line for line in git_output(repo, "rev-list", "--max-parents=0", "HEAD").splitlines() if line)
    if not roots:
        raise ProofUnavailable("repository_identity_failed", "repository has no root commit")
    common_dir_value = git_output(repo, "rev-parse", "--git-common-dir")
    common_dir = Path(common_dir_value)
    if not common_dir.is_absolute():
        common_dir = repo / common_dir
    repository_id = roots[0][:12]
    identity = {
        "kind": IDENTITY_KIND,
        "environment_sha256": environment_fingerprint(evidence.get("environment"), gate_cwd),
        "gate": {
            "command_sha256": sha256_bytes(command.encode("utf-8")),
            "cwd": normalized_cwd,
            "name": name,
            "scope": scope,
        },
        "repository": {
            "common_dir_sha256": sha256_bytes(str(common_dir.resolve()).encode("utf-8")),
            "head": git_output(repo, "rev-parse", "HEAD"),
            "roots": roots,
            "tree": git_output(repo, "rev-parse", "HEAD^{tree}"),
        },
        "selection": {
            "base_commit": base_commit,
            "changed_file_count": len(changed_files),
            "changed_files_sha256": sha256_bytes(canonical_json(changed_files)),
        },
        "workflow_sha256": sha256_file(workflow_path),
    }
    labels = {"name": name, "scope": scope, "cwd": normalized_cwd, "command": command}
    return identity, repository_id, labels


def proof_path(repository_id: str, proof_key: str) -> Path:
    return state_dir() / "gate-proofs" / repository_id / f"{proof_key}.json"


@contextmanager
def proof_lock(repository_id: str) -> Iterator[None]:
    lock_path = state_dir() / "gate-proofs" / repository_id / ".lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def artifact_record(path: Path) -> dict[str, str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ProofUnavailable("artifact_missing", f"gate artifact is missing: {resolved}")
    return {"path": str(resolved), "sha256": sha256_file(resolved)}


def validate_envelope(envelope: dict[str, Any], labels: dict[str, str], expected_proof_key: str) -> None:
    if envelope.get("status") != "pass":
        raise ProofUnavailable("gate_not_passing", "only passing gate evidence can be recorded")
    envelope_proof_key = envelope.get("proof_key")
    if not isinstance(envelope_proof_key, str) or not envelope_proof_key:
        raise ProofUnavailable("envelope_proof_key_missing", "gate envelope is not bound to a pre-execution proof key")
    if envelope_proof_key != expected_proof_key:
        raise ProofUnavailable("envelope_proof_key_mismatch", "gate envelope proof key does not match the expected proof key")
    gate = envelope.get("gate")
    if not isinstance(gate, dict):
        raise ProofUnavailable("envelope_invalid", "gate envelope is missing gate metadata")
    for key in ("name", "scope", "cwd", "command"):
        if gate.get(key) != labels[key]:
            raise ProofUnavailable("envelope_mismatch", f"gate envelope {key} does not match the proof request")


def ledger_repository_common_dir_sha256(run: dict[str, Any]) -> str:
    raw_repo = run.get("repo")
    if not isinstance(raw_repo, str) or not raw_repo:
        raise ProofUnavailable("ledger_repository_unverifiable", "run ledger has no repository provenance")
    ledger_repo = Path(raw_repo).resolve()
    if not ledger_repo.is_dir():
        raise ProofUnavailable("ledger_repository_unverifiable", "run ledger repository is unavailable")
    try:
        common_dir_value = git_output(ledger_repo, "rev-parse", "--git-common-dir")
    except ProofUnavailable as exc:
        raise ProofUnavailable("ledger_repository_unverifiable", "run ledger repository cannot be verified") from exc
    common_dir = Path(common_dir_value)
    if not common_dir.is_absolute():
        common_dir = ledger_repo / common_dir
    return sha256_bytes(str(common_dir.resolve()).encode("utf-8"))


def ledger_run_dir(
    envelope_path: Path,
    run_id: str,
    repository_id: str,
    common_dir_sha256: str,
) -> Path:
    if not RUN_ID_SEGMENT.fullmatch(run_id) or run_id in {".", ".."}:
        raise ProofUnavailable("request_invalid", "run id must be a path-safe segment")
    resolved = envelope_path.resolve()
    runs_root = (state_dir() / "runs").resolve()
    try:
        relative = resolved.relative_to(runs_root)
    except ValueError as exc:
        raise ProofUnavailable("envelope_not_ledger", "gate envelope must be stored under the run ledger") from exc
    parts = relative.parts
    if len(parts) >= 6 and parts[2] == run_id and parts[3:5] == ("artifacts", "gates"):
        run_dir = runs_root.joinpath(*parts[:3])
    elif len(parts) >= 5 and parts[1] == run_id and parts[2:4] == ("artifacts", "gates"):
        run_dir = runs_root.joinpath(*parts[:2])
    else:
        raise ProofUnavailable("envelope_not_ledger", "gate envelope path does not match a run-ledger gate artifact")
    if resolved.name != "envelope.json":
        raise ProofUnavailable("envelope_not_ledger", "gate envelope must use the immutable envelope.json artifact path")
    run = read_json(run_dir / "run.json")
    if run.get("kind") != "run-ledger-v1" or run.get("run_id") != run_id:
        raise ProofUnavailable("envelope_not_ledger", "gate envelope does not belong to the declared run")
    if run.get("repo_hash") != repository_id:
        raise ProofUnavailable("ledger_repository_mismatch", "run ledger belongs to a different repository history")
    if ledger_repository_common_dir_sha256(run) != common_dir_sha256:
        raise ProofUnavailable("ledger_repository_mismatch", "run ledger belongs to different shared Git storage")
    return run_dir


def artifact_records(envelope_path: Path, envelope: dict[str, Any], run_dir: Path) -> list[dict[str, str]]:
    artifacts = [artifact_record(envelope_path)]
    raw_logs = envelope.get("raw_logs")
    if isinstance(raw_logs, dict) and raw_logs.get("path"):
        raw_path = Path(str(raw_logs["path"])).resolve()
        try:
            raw_path.relative_to(run_dir.resolve())
        except ValueError as exc:
            raise ProofUnavailable("artifact_not_ledger", "gate raw logs must be stored under the declared run") from exc
        artifacts.append(artifact_record(raw_path))
    return artifacts


def rerun(reason: str, message: str, proof_key: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": DECISION_KIND,
        "decision": "rerun",
        "reason": reason,
        "summary": message,
    }
    if proof_key:
        payload["proof_key"] = proof_key
    return payload


def lookup(request: dict[str, Any], repo: Path) -> dict[str, Any]:
    try:
        identity, repository_id, _ = compute_identity(request, repo)
    except ProofUnavailable as exc:
        return rerun(exc.code, exc.message)
    key = sha256_bytes(canonical_json(identity))
    path = proof_path(repository_id, key)
    if not path.is_file():
        return rerun("proof_missing", "no exact gate proof was recorded", key)
    try:
        proof = read_json(path)
    except (OSError, json.JSONDecodeError, ProofUnavailable):
        return rerun("proof_corrupt", "stored gate proof could not be parsed", key)
    if proof.get("kind") != PROOF_KIND or proof.get("proof_key") != key or proof.get("identity") != identity:
        return rerun("proof_mismatch", "stored gate proof does not match its content key", key)
    artifacts = proof.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return rerun("proof_corrupt", "stored gate proof has no artifacts", key)
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str) or not isinstance(artifact.get("sha256"), str):
            return rerun("proof_corrupt", "stored gate proof has malformed artifact metadata", key)
        artifact_path = Path(artifact["path"])
        if not artifact_path.is_file():
            return rerun("artifact_missing", "a recorded gate artifact is missing", key)
        if sha256_file(artifact_path) != artifact["sha256"]:
            return rerun("artifact_changed", "a recorded gate artifact changed", key)
    return {
        "kind": DECISION_KIND,
        "decision": "reuse",
        "reason": "exact_match",
        "proof_key": key,
        "proof_path": str(path),
        "source": proof.get("source"),
        "summary": "exact passing gate proof is reusable",
    }


def record(
    request: dict[str, Any],
    repo: Path,
    envelope_path: Path,
    run_id: str,
    expected_proof_key: str | None,
) -> dict[str, Any]:
    if not isinstance(expected_proof_key, str) or not expected_proof_key:
        return {
            "kind": RECORD_KIND,
            "status": "skipped",
            "reason": "expected_proof_key_missing",
            "summary": "recording requires the proof key captured before gate execution",
        }
    try:
        identity, repository_id, labels = compute_identity(request, repo)
        key = sha256_bytes(canonical_json(identity))
        if key != expected_proof_key:
            raise ProofUnavailable("identity_changed", "proof identity changed after the gate decision")
        envelope = read_json(envelope_path)
        run_dir = ledger_run_dir(
            envelope_path,
            run_id,
            repository_id,
            identity["repository"]["common_dir_sha256"],
        )
        validate_envelope(envelope, labels, expected_proof_key)
        artifacts = artifact_records(envelope_path, envelope, run_dir)
    except (OSError, json.JSONDecodeError) as exc:
        return {"kind": RECORD_KIND, "status": "skipped", "reason": "artifact_invalid", "summary": str(exc)}
    except ProofUnavailable as exc:
        return {"kind": RECORD_KIND, "status": "skipped", "reason": exc.code, "summary": exc.message}

    path = proof_path(repository_id, key)
    proof = {
        "artifacts": artifacts,
        "gate": {key: labels[key] for key in ("name", "scope", "cwd")},
        "identity": identity,
        "kind": PROOF_KIND,
        "proof_key": key,
        "source": {"envelope_path": str(envelope_path.resolve()), "run_id": run_id},
    }
    with proof_lock(repository_id):
        write_json(path, proof)
    return {
        "kind": RECORD_KIND,
        "status": "recorded",
        "proof_key": key,
        "proof_path": str(path),
        "summary": "exact passing gate proof recorded",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    lookup_parser = subparsers.add_parser("lookup")
    lookup_parser.add_argument("--request-file", required=True)
    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--request-file", required=True)
    record_parser.add_argument("--envelope-file", required=True)
    record_parser.add_argument("--run-id", required=True)
    record_parser.add_argument("--expected-proof-key")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = repo_root()
    try:
        request = read_json(Path(args.request_file))
    except (OSError, json.JSONDecodeError, ProofUnavailable) as exc:
        code = exc.code if isinstance(exc, ProofUnavailable) else "request_invalid"
        message = exc.message if isinstance(exc, ProofUnavailable) else str(exc)
        payload = rerun(code, message) if args.command == "lookup" else {
            "kind": RECORD_KIND,
            "status": "skipped",
            "reason": code,
            "summary": message,
        }
    else:
        if args.command == "lookup":
            payload = lookup(request, repo)
        else:
            payload = record(request, repo, Path(args.envelope_file), args.run_id, args.expected_proof_key)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
