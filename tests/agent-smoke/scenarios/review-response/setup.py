#!/usr/bin/env python3
"""Create a local review-response smoke fixture."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCENARIO_DIR = Path(__file__).resolve().parent


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr}")
    return result.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    mock_bin = run_dir / "mock-bin"
    gh_log = run_dir / "gh.log"
    source_log = run_dir / "pr-review-source.log"
    update_log = run_dir / "pr-review-update.log"
    update_payload = run_dir / "pr-review-update-payload.json"
    gate_marker = run_dir / "validate-fixture.marker"
    origin = run_dir / "origin.git"
    repo = run_dir / "repo"

    mock_bin.mkdir(parents=True, exist_ok=True)
    for name in ["gh", "pr-review-source", "pr-review-update"]:
        shutil.copy2(SCENARIO_DIR / "mock-bin" / name, mock_bin / name)
        os.chmod(mock_bin / name, 0o755)

    run(["git", "init", "--bare", str(origin)])
    run(["git", "clone", str(origin), str(repo)])
    run(["git", "config", "user.email", "review-response-smoke@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Beislid Review Response Smoke"], cwd=repo)

    write(repo / ".beislid" / "workflow.md", """<!-- beislid-workflow: v1 -->

# Review-response smoke workflow

## PR target

```beislid:pr_base.default
main
```

```beislid:pr_host.owner
sandsower
```

```beislid:pr_host.repo
review-response-smoke
```

```beislid:branch_pattern
^(\\d+)-
```

## PR reviews

```beislid:pr_review_source
type: cli
summary_command: 'pr-review-source summary {owner} {repo} {number} {url}'
threads_command: 'pr-review-source threads {owner} {repo} {number} {url}'
```

```beislid:pr_review_update
type: cli
reply_command: 'pr-review-update reply {json_file}'
```

## Quality gates

```beislid:gates
- name: validate-fixture
  command: 'python3 scripts/validate.py'
```

## Probe cache

```beislid:probe_cache
ttl_hours: 1
```
""")
    write(repo / "src" / "reply.py", """def greeting():
    return 'heya reviewer'
""")
    write(repo / "scripts" / "validate.py", """from pathlib import Path

text = Path('src/reply.py').read_text(encoding='utf-8')
if "return 'hello reviewer'" not in text:
    raise SystemExit("expected greeting to return hello reviewer")
marker_value = __import__('os').environ.get('REVIEW_RESPONSE_GATE_MARKER')
if marker_value:
    marker = Path(marker_value)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('validate-fixture ran\\n', encoding='utf-8')
print('ok: validate-fixture passed')
""")
    write(repo / "README.md", "# Review-response smoke fixture\n\nReview feedback targets `src/reply.py`.\n")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "Initial review-response smoke fixture"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "push", "-u", "origin", "main"], cwd=repo)
    run(["git", "checkout", "-b", "123-review-response-review"], cwd=repo)
    run(["git", "push", "-u", "origin", "123-review-response-review"], cwd=repo)

    metadata: dict[str, object] = {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "gh_log": str(gh_log),
        "pr_review_source_log": str(source_log),
        "pr_review_update_log": str(update_log),
        "pr_review_update_payload": str(update_payload),
        "gate_marker": str(gate_marker),
        "origin": str(origin),
        "branch": "123-review-response-review",
        "base": "main",
        "pr_number": 7,
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
            "GH_MOCK_LOG": str(gh_log),
            "PR_REVIEW_SOURCE_LOG": str(source_log),
            "PR_REVIEW_UPDATE_LOG": str(update_log),
            "PR_REVIEW_UPDATE_PAYLOAD_COPY": str(update_payload),
            "REVIEW_RESPONSE_GATE_MARKER": str(gate_marker),
        },
        "path_prepend": [str(mock_bin)],
    }
    write(run_dir / "metadata.json", json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir")
    args = parser.parse_args()
    if args.run_dir:
        run_dir = Path(args.run_dir).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(tempfile.mkdtemp(prefix=f"beislid-review-response-smoke-{stamp}-"))
    print(json.dumps(create_fixture(run_dir), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
