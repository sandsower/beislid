#!/usr/bin/env python3
"""Host-side workflow-signal heartbeat for Claude Code lifecycle hooks.

Skills only emit signals at semantic boundaries, and only when the model
remembers to run the CLI. This hook makes the signal surface trustworthy by
emitting model-independent heartbeats at host lifecycle events:

  UserPromptSubmit -> working   (user handed the agent work)
  Stop             -> waiting   (agent finished its turn, waiting on the user)
  SessionEnd       -> done      (session over; also clears the tmux marker)

Heartbeats carry no --skill/--phase context beyond `heartbeat`; skill-level
emissions remain the richer signal and simply overwrite the heartbeat state
at their own boundaries.

Best-effort by design: every failure path exits 0 and prints nothing.
Only fires inside a git worktree whose root has `.beislid/workflow.md`.
Stdlib-only.

Register in ~/.claude/settings.json (see docs/workflow-signals.md):
UserPromptSubmit, Stop, and SessionEnd hooks all pointing at this script.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

EVENT_STATES = {
    "UserPromptSubmit": "working",
    "Stop": "waiting",
    "SessionEnd": "done",
}

RUN_TIMEOUT_SECONDS = 3


def _repo_root(cwd: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    root = result.stdout.strip()
    return root or None


def _run_quiet(argv: list[str]) -> None:
    try:
        subprocess.run(
            argv,
            capture_output=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    state = EVENT_STATES.get(payload.get("hook_event_name", ""))
    if not state:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    root = _repo_root(cwd)
    if not root or not os.path.isfile(os.path.join(root, ".beislid", "workflow.md")):
        return 0

    beislid = shutil.which("beislid")
    if beislid:
        _run_quiet(
            [beislid, "workflow-signal", "emit", state, "--phase", "heartbeat", "--repo", root]
        )

    # `done` leaves the tmux marker showing a stale checkmark; clear it so the
    # window reads idle after the session ends.
    if state == "done" and os.environ.get("TMUX") and shutil.which("tmux-glance"):
        _run_quiet(["tmux-glance", "clear"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
