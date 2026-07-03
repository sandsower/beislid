#!/usr/bin/env python3
"""Create a local review-response smoke fixture."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_and_push, init_fixture_repo, run, setup_main, write, write_gh_mock, write_workflow, write_mock_script


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    mock_bin = run_dir / "mock-bin"
    gh_log = run_dir / "gh.log"
    source_log = run_dir / "pr-review-source.log"
    update_log = run_dir / "pr-review-update.log"
    update_payload = run_dir / "pr-review-update-payload.json"
    gate_marker = run_dir / "validate-fixture.marker"

    write_gh_mock(mock_bin / "gh", routes=[
        {
            "match": "pr view",
            "response": (
                '{"url":"https://example.invalid/sandsower/review-response-smoke/pull/7",'
                '"number":7,"baseRefName":"main","headRefName":"123-review-response-review"}'
            ),
        },
    ])

    pr_review_source_body = """cmd=${1:-}
expected_owner=sandsower
expected_repo=review-response-smoke
expected_number=7
expected_url=https://example.invalid/sandsower/review-response-smoke/pull/7
if [[ $# -ne 5 || "${2:-}" != "$expected_owner" || "${3:-}" != "$expected_repo" || "${4:-}" != "$expected_number" || "${5:-}" != "$expected_url" ]]; then
  echo "mock pr-review-source: expected <summary|threads> $expected_owner $expected_repo $expected_number $expected_url, got: $*" >&2
  exit 46
fi
case "$cmd" in
  summary)
    cat <<'JSON'
{"url":"https://example.invalid/sandsower/review-response-smoke/pull/7","number":7,"reviewDecision":"CHANGES_REQUESTED","comments":[],"reviews":[{"author":{"login":"review-responder"},"state":"CHANGES_REQUESTED","body":"One inline thread is unresolved."}]}
JSON
    ;;
  threads)
    cat <<'JSON'
[
  {
    "id": 7001,
    "path": "src/reply.py",
    "line": 2,
    "body": "Please return `hello reviewer` instead of the casual `heya reviewer`.",
    "user": {"login": "review-responder"},
    "html_url": "https://example.invalid/sandsower/review-response-smoke/pull/7#discussion_r7001"
  }
]
JSON
    ;;
  *)
    echo "mock pr-review-source: unsupported command: $*" >&2
    exit 45
    ;;
esac
"""
    write_mock_script(mock_bin / "pr-review-source", log_env="PR_REVIEW_SOURCE_LOG", command_name="pr-review-source", body=pr_review_source_body)

    pr_review_update_body = """out=${PR_REVIEW_UPDATE_PAYLOAD_COPY:-}
if [[ -z "$out" ]]; then
  echo "PR_REVIEW_UPDATE_PAYLOAD_COPY must be set" >&2
  exit 98
fi
mkdir -p "$(dirname "$out")"
if [[ $# -ne 2 || "${1:-}" != "reply" ]]; then
  echo "pr-review-update requires exactly: reply <json_file>" >&2
  exit 40
fi
json_file=$2
if [[ ! -f "$json_file" ]]; then
  echo "pr-review-update expected a real json_file path, got $json_file" >&2
  exit 42
fi
case "$json_file" in
  *$'\\n'*)
    echo "pr-review-update got raw-looking JSON instead of path" >&2
    exit 43
    ;;
esac
cp "$json_file" "$out"
echo "ok: PR review reply posted"
"""
    write_mock_script(mock_bin / "pr-review-update", log_env="PR_REVIEW_UPDATE_LOG", command_name="pr-review-update", body=pr_review_update_body)

    origin, repo = init_fixture_repo(run_dir, name="Beislid Review Response Smoke", email="review-response-smoke@example.invalid")

    write_workflow(repo, """<!-- beislid-workflow: v1 -->

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
    commit_and_push(repo, "Initial review-response smoke fixture")
    run(["git", "checkout", "-b", "123-review-response-review"], cwd=repo)
    run(["git", "push", "-u", "origin", "123-review-response-review"], cwd=repo)

    return {
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


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-review-response-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
