#!/usr/bin/env python3
"""Create a local /setup first-run smoke fixture."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_only, init_plain_repo, run, setup_main, write, write_gh_mock

REMOTE_URL = "https://github.com/sandsower/setup-smoke.git"


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    mock_bin = run_dir / "mock-bin"
    gh_log = run_dir / "gh.log"

    write_gh_mock(mock_bin / "gh", routes=[
        {"match": "repo view", "response": "main"},
    ])

    repo = init_plain_repo(run_dir, name="Beislid Setup Smoke", email="setup-smoke@example.invalid")
    run(["git", "remote", "add", "origin", REMOTE_URL], cwd=repo)

    write(repo / "src" / "app.py", "def greet():\n    return 'hi'\n")
    commit_only(repo, "123 Initial app scaffold")
    write(repo / "src" / "app.py", "def greet():\n    return 'hello'\n")
    commit_only(repo, "124 Fix greeting text", paths=["src/app.py"])
    write(repo / "README.md", "# Setup smoke fixture\n")
    commit_only(repo, "125 Add README", paths=["README.md"])

    for branch in ["123-fix-login", "124-add-feature", "125-tidy-readme"]:
        run(["git", "branch", branch], cwd=repo)

    initial_head = run(["git", "rev-parse", "HEAD"], cwd=repo)

    return {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "remote_url": REMOTE_URL,
        "initial_head": initial_head,
        "gh_log": str(gh_log),
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
            "GH_MOCK_LOG": str(gh_log),
        },
        "path_prepend": [str(mock_bin)],
    }


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-setup-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
