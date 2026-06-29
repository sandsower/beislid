from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .hosts import get_host


MANIFEST = "host-links-before.json"
LOCK = ".beislid-agent-smoke-lock.json"


def beislid_skills(worktree: Path) -> list[tuple[str, Path]]:
    skills_root = worktree / "skills"
    skills: list[tuple[str, Path]] = []
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        skill_dir = skill_md.parent
        skills.append((skill_dir.name, skill_dir))
    if not skills:
        raise SystemExit(f"no Beislið skills found under {skills_root}")
    return skills


def _state(path: Path) -> dict[str, str | None]:
    if path.is_symlink():
        return {"state": "symlink", "target": os.readlink(path)}
    if not path.exists():
        return {"state": "missing", "target": None}
    if path.is_dir():
        return {"state": "directory", "target": None}
    return {"state": "file", "target": None}


def _lock_path(skills_dir: Path) -> Path:
    return skills_dir / LOCK


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _acquire_lock(host_name: str, skills_dir: Path, run_dir: Path, worktree: Path) -> None:
    lock_path = _lock_path(skills_dir)
    payload = {"host": host_name, "run_dir": str(run_dir), "worktree": str(worktree)}
    fd, temp_name = tempfile.mkstemp(prefix=f".{LOCK}.", dir=str(skills_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.link(temp_name, lock_path)
        except FileExistsError:
            try:
                lock = _read_json(lock_path)
            except Exception as exc:
                raise SystemExit(f"could not read lock {lock_path}: {exc}") from exc
            if lock.get("run_dir") != str(run_dir):
                raise SystemExit(
                    f"{host_name} skills are already locked by another smoke run: {lock.get('run_dir')}. "
                    f"Run cleanup for that run before starting another {host_name} smoke."
                )
            return
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _release_lock(skills_dir: Path, run_dir: Path, warnings: list[str]) -> None:
    lock_path = _lock_path(skills_dir)
    if not lock_path.exists():
        return
    try:
        lock = _read_json(lock_path)
    except Exception as exc:
        warnings.append(f"could not read lock {lock_path}: {exc}")
        return
    if lock.get("run_dir") == str(run_dir):
        lock_path.unlink()
    else:
        warnings.append(f"left lock for another run in place: {lock_path}")


def activate(run_dir: Path) -> None:
    meta = _read_json(run_dir / "agent-smoke.json")
    host = get_host(meta["host"])
    worktree = Path(meta["worktree"])
    manifest_path = run_dir / MANIFEST
    if manifest_path.exists():
        return

    host.skills_dir.mkdir(parents=True, exist_ok=True)
    _acquire_lock(host.name, host.skills_dir, run_dir, worktree)

    entries = []
    for name, source in beislid_skills(worktree):
        dest = host.skills_dir / name
        before = _state(dest)
        if before["state"] not in {"missing", "symlink"}:
            _release_lock(host.skills_dir, run_dir, [])
            raise SystemExit(f"refusing to replace non-symlink host skill path: {dest} ({before['state']})")
        entries.append({"name": name, "path": str(dest), "before": before, "new_target": str(source)})

    # Write the manifest before mutation so cleanup can recover if a later unlink/symlink fails.
    _write_json(manifest_path, {"host": host.name, "skills_dir": str(host.skills_dir), "entries": entries})

    try:
        for entry in entries:
            dest = Path(entry["path"])
            source = Path(entry["new_target"])
            if dest.exists() or dest.is_symlink():
                dest.unlink()
            dest.symlink_to(source)
    except Exception:
        cleanup(run_dir)
        raise


def cleanup(run_dir: Path) -> None:
    manifest_path = run_dir / MANIFEST
    warnings: list[str] = []
    if not manifest_path.exists():
        meta_path = run_dir / "agent-smoke.json"
        if meta_path.exists():
            meta = _read_json(meta_path)
            host = get_host(meta["host"])
            _release_lock(host.skills_dir, run_dir, warnings)
            (run_dir / "host-links-cleanup.json").write_text(json.dumps({"warnings": warnings}, indent=2) + "\n")
        return

    manifest = _read_json(manifest_path)
    for entry in manifest.get("entries", []):
        path = Path(entry["path"])
        before = entry["before"]
        new_target = entry["new_target"]
        current_is_ours = path.is_symlink() and os.readlink(path) == new_target

        if before["state"] == "missing":
            if current_is_ours:
                path.unlink()
            elif path.exists() or path.is_symlink():
                warnings.append(f"left changed path in place (was missing): {path}")
        elif before["state"] == "symlink":
            old_target = before["target"]
            if current_is_ours:
                path.unlink()
                path.symlink_to(old_target)
            elif not path.exists() and not path.is_symlink():
                path.symlink_to(old_target)
            else:
                warnings.append(f"left changed path in place (not smoke symlink): {path}")

    skills_dir = Path(manifest.get("skills_dir", "")) if manifest.get("skills_dir") else None
    if skills_dir:
        _release_lock(skills_dir, run_dir, warnings)
    (run_dir / "host-links-cleanup.json").write_text(json.dumps({"warnings": warnings}, indent=2) + "\n")
