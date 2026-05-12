from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Host:
    name: str
    command: str
    skills_dir: Path


HOSTS = {
    "claude": Host("claude", "claude", Path.home() / ".claude" / "skills"),
    "codex": Host("codex", "codex", Path.home() / ".codex" / "skills"),
}


def get_host(name: str) -> Host:
    try:
        return HOSTS[name]
    except KeyError as exc:
        supported = ", ".join(sorted(HOSTS))
        raise SystemExit(f"unsupported host {name!r}; supported hosts: {supported}. Pi support is not wired yet.") from exc
