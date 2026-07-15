#!/usr/bin/env python3
"""Verify a host-agent /setup first-run smoke run."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_only, init_plain_repo, run, write
from harness.verification import collect_agent_output, fail, require_stamp_sequence

REQUIRED_STAMPS = [
    "✓ setup/router v1 loaded",
    "✓ setup/first-run v1 loaded",
    "✓ setup/write-and-report v1 loaded",
    "✓ setup/agents-integration v1 loaded",
]


def load_metadata(run_dir: Path) -> dict:
    path = run_dir / "metadata.json"
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    repo = Path(metadata["repo"])
    initial_head = metadata["initial_head"]
    gh_log = Path(metadata["gh_log"])

    workflow_path = repo / ".beislid" / "workflow.md"
    if not workflow_path.is_file():
        fail(errors, "product", "setup did not write .beislid/workflow.md")
        workflow_text = ""
    else:
        workflow_text = workflow_path.read_text(encoding="utf-8", errors="replace")

    if not workflow_text.startswith("<!-- beislid-workflow: v1 -->"):
        fail(errors, "product", "workflow.md missing the version stamp on line 1")

    ticket_source_match = re.search(r"```beislid:ticket_source\n(.*?)```", workflow_text, re.DOTALL)
    if not ticket_source_match:
        fail(errors, "product", "workflow.md missing a beislid:ticket_source block")
    else:
        block = ticket_source_match.group(1)
        if "type: cli" not in block:
            fail(errors, "product", "ticket_source block must be type: cli")
        if "gh issue view" not in block:
            fail(errors, "product", "ticket_source command must use gh issue view")
        if "^#?\\d+$" not in block and "^#?\\d+$".replace("\\\\", "\\") not in block:
            fail(errors, "product", "ticket_source id_pattern must be '^#?\\d+$'")

    if "```beislid:branch_pattern" not in workflow_text or "^(\\d+)-" not in workflow_text:
        fail(errors, "product", "workflow.md missing branch_pattern block '^(\\d+)-'")

    if "ttl_hours: 24" not in workflow_text:
        fail(errors, "product", "workflow.md probe_cache must default to ttl_hours: 24 on first run")

    if "pr_base" in workflow_text:
        fail(errors, "product", "pr_base resolved to the silent default 'main' and must not appear in workflow.md at all")

    agents_path = repo / "AGENTS.md"
    if not agents_path.is_file():
        fail(errors, "product", "setup did not create/update AGENTS.md")
    elif "## Agent skills" not in agents_path.read_text(encoding="utf-8", errors="replace"):
        fail(errors, "product", "AGENTS.md missing the '## Agent skills' bootstrap block")

    head = run(["git", "-C", str(repo), "rev-parse", "HEAD"])
    if head != initial_head:
        fail(errors, "product", "setup must not commit workflow.md/AGENTS.md itself - a new commit was made")

    gh_text = gh_log.read_text(encoding="utf-8", errors="replace") if gh_log.exists() else ""
    if "gh auth status" not in gh_text:
        fail(errors, "product", "setup never ran the targeted-inspection gh auth status probe")
    if re.search(r"gh issue view \d", gh_text):
        fail(errors, "product", "setup fetched a real ticket during configuration; it should only configure ticket_source, not use it")

    host_text = collect_agent_output(run_dir, skip_names={"gh.log"}, strip_tokens=True)
    require_stamp_sequence(
        errors,
        text=host_text,
        stamps=REQUIRED_STAMPS,
        label="agent output",
        kind="verifier",
    )

    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-setup-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        repo = init_plain_repo(run_dir, name="Self Test", email="selftest@example.invalid")
        write(repo / "README.md", "hello\n")
        commit_only(repo, "123 initial")
        initial_head = run(["git", "rev-parse", "HEAD"], cwd=repo)

        write(repo / ".beislid" / "workflow.md", """<!-- beislid-workflow: v1 -->

# Setup smoke workflow

```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json title,body,labels'
id_pattern: '^#?\\d+$'
```

```beislid:branch_pattern
^(\\d+)-
```

```beislid:probe_cache
ttl_hours: 24
```
""")
        write(repo / "AGENTS.md", "# Repo guidance\n\n## Agent skills\n\nRead `.beislid/workflow.md` first.\n")

        gh_log = run_dir / "gh.log"
        write(gh_log, f"2026-01-01T00:00:00Z\tcwd={repo}\tgh auth status\n2026-01-01T00:00:01Z\tcwd={repo}\tgh repo view --json defaultBranchRef -q .defaultBranchRef.name\n")

        metadata = {
            "repo": str(repo),
            "initial_head": initial_head,
            "gh_log": str(gh_log),
        }
        write(run_dir / "metadata.json", json.dumps(metadata, indent=2) + "\n")
        write(run_dir / "agent.log", "\n".join(REQUIRED_STAMPS) + "\n")

        errors = verify(run_dir)
        if errors:
            print("self-test failed (expected pass):", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        write(run_dir / "agent.log", "✓ setup/router v1 loaded\n✓ setup/first-run v1 loaded\n")
        missing_stamp_errors = verify(run_dir)
        if not any("expected aux load stamps" in error for error in missing_stamp_errors):
            print("self-test failed: missing setup aux stamps should fail", file=sys.stderr)
            return 1
        write(run_dir / "agent.log", "\n".join(REQUIRED_STAMPS) + "\n")

        # Negative 1: pr_base leaked into workflow.md despite the silent 'main' default.
        write(repo / ".beislid" / "workflow.md", workflow_path_text(repo) + "\n```beislid:pr_base.default\nmain\n```\n")
        negative_pr_base = verify(run_dir)
        if not any("pr_base" in error for error in negative_pr_base):
            print("self-test failed: leaked pr_base section should fail", file=sys.stderr)
            return 1

        # Negative 2: setup committed its own output.
        write(repo / ".beislid" / "workflow.md", workflow_path_text(repo))
        commit_only(repo, "setup committed its own config", paths=[".beislid/workflow.md"])
        negative_commit = verify(run_dir)
        if not any("must not commit" in error for error in negative_commit):
            print("self-test failed: setup committing its own output should fail", file=sys.stderr)
            return 1

        print("ok: setup verify self-test passed")
        return 0


def workflow_path_text(repo: Path) -> str:
    return (repo / ".beislid" / "workflow.md").read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.run_dir:
        parser.error("run_dir is required unless --self-test is used")
    errors = verify(Path(args.run_dir).resolve())
    if errors:
        print("setup smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: setup agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
