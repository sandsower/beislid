#!/usr/bin/env python3
"""Verify a host-agent ready-for-review smoke run created by setup.py."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_TRANSCRIPT_PATTERNS = [
    ("phase-1 aux load", r"phase-1-detect"),
    ("phase-2 aux load", r"phase-2-gates"),
    ("phase-3 aux load", r"phase-3-review"),
    ("phase-4 aux load", r"phase-4-submit"),
    ("Phase 1 marker", r"phase\s*1"),
    ("Phase 2 marker", r"phase\s*2"),
    ("Phase 3 marker", r"phase\s*3"),
    ("Phase 4 marker", r"phase\s*4"),
    ("fast-path marker", r"fast[- ]path"),
    ("combined review marker", r"combined review|combined review/final-check|combined review/fresh-eyes"),
    ("fixture gate evidence", r"validate-fixture|ok:\s*fixture validated"),
    ("skills gate evidence", r"validate-skills-area|ok:\s*skills area validated"),
    ("gate-set selection evidence", r"gate[-_ ]sets?|selector|docs-files"),
    ("gate-set skip evidence", r"workflows-should-skip|workflow-files|skipped"),
    ("push side effect", r"\bpush(?:ed)?\b|git push"),
    ("PR creation side effect", r"pr create|PR opened|Opened PR|pull/1"),
]

REQUIRED_LOADED_AUX = ["phase-1-detect", "phase-2-gates", "phase-3-review", "phase-4-submit"]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_metadata(run_dir: Path) -> dict:
    path = run_dir / "metadata.json"
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_loaded_aux(values: list[object]) -> set[str]:
    normalized: set[str] = set()
    for value in values:
        for part in str(value).split(","):
            name = Path(part.strip()).name
            if name.endswith(".md"):
                name = name[:-3]
            if name.startswith("ready-for-review/"):
                name = name.split("/", 1)[1]
            if name:
                normalized.add(name)
    return normalized


def duplicate_approval_prompt_errors(text: str) -> list[str]:
    """Return smoke failures for duplicated visible hard-gate approval prompts."""
    pr_approval_lines: list[str] = []
    commit_approval_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "?" not in line or not re.search(r"\bapprov(?:e|al|ing)\b", line, re.IGNORECASE):
            continue
        if re.search(r"\b(push|pushing|pr|pull request|creating this pr|create(?:ing)? the pr)\b", line, re.IGNORECASE):
            pr_approval_lines.append(line)
        if re.search(r"\b(commit|committing|autofix|fix)\b", line, re.IGNORECASE):
            commit_approval_lines.append(line)

    errors: list[str] = []
    if len(pr_approval_lines) > 1:
        errors.append("duplicate visible PR approval prompts: " + " | ".join(pr_approval_lines))
    if len(commit_approval_lines) > 1:
        errors.append("duplicate visible commit/autofix approval prompts: " + " | ".join(commit_approval_lines))
    return errors


def extract_transcript_memory(text: str) -> dict:
    match = re.search(
        r"kind:\s*ready-for-review-session-memory-v1\s*```json\s*(\{.*?\})\s*```",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def verify_memory_fields(errors: list[str], memory: dict, transcript: Path, metadata: dict, source: str) -> None:
    branch = metadata["branch"]
    base = metadata["base"]
    pr_url = metadata.get("env", {}).get("GH_MOCK_PR_URL", "https://example.invalid/beislid-smoke/pull/1")
    memory_evidence = memory.get("evidence") if isinstance(memory.get("evidence"), dict) else {}
    ticket = memory.get("ticket") if isinstance(memory.get("ticket"), dict) else {}
    pr = memory.get("pr") if isinstance(memory.get("pr"), dict) else {}

    if memory.get("kind") != "ready-for-review-session-memory-v1":
        fail(errors, f"{source} memory object missing ready-for-review-session-memory-v1 kind")
    if memory.get("branch") != branch:
        fail(errors, f"{source} memory marker branch mismatch: expected {branch!r}, got {memory.get('branch')!r}")
    if memory.get("base") != base:
        fail(errors, f"{source} memory marker base mismatch: expected {base!r}, got {memory.get('base')!r}")
    if str(ticket.get("id", "")).lower() != "none":
        fail(errors, f"{source} memory marker ticket id should be none, got {ticket.get('id')!r}")
    if pr_url and pr.get("url") != pr_url:
        fail(errors, f"{source} memory marker PR URL mismatch: expected {pr_url!r}, got {pr.get('url')!r}")
    if memory.get("phase_path") != "new-pr-fast-path":
        fail(errors, f"{source} memory marker phase_path should be new-pr-fast-path, got {memory.get('phase_path')!r}")
    if not re.search(r"parallel", str(memory_evidence.get("gates", "")), re.IGNORECASE):
        fail(errors, f"{source} memory marker gates should record fast-path parallel/sequential mode")
    if not re.search(r"combined review", str(memory_evidence.get("review", "")), re.IGNORECASE):
        fail(errors, f"{source} memory marker review should record combined review")
    if Path(str(memory_evidence.get("transcript", ""))).resolve() != transcript.resolve():
        fail(errors, f"{source} memory marker evidence transcript path does not match transcript artifact")
    loaded_raw = memory_evidence.get("loaded_aux_files") if isinstance(memory_evidence.get("loaded_aux_files"), list) else []
    loaded = normalize_loaded_aux(loaded_raw)
    for aux in REQUIRED_LOADED_AUX:
        if aux not in loaded:
            fail(errors, f"{source} memory marker missing loaded aux file: {aux}")


def verify_evidence_json(errors: list[str], transcript: Path, metadata: dict) -> None:
    evidence_path = transcript.parent / "evidence.json"
    if not evidence_path.exists():
        fail(errors, f"missing smoke evidence artifact beside transcript: {evidence_path}")
        return
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(errors, f"smoke evidence artifact is not valid JSON: {evidence_path}: {exc}")
        return

    memory = evidence.get("memory") if isinstance(evidence.get("memory"), dict) else {}

    if evidence.get("kind") != "ready-for-review-smoke-evidence-v1":
        fail(errors, f"smoke evidence has wrong kind: {evidence.get('kind')!r}")
    if not evidence.get("finalized"):
        fail(errors, "smoke evidence was not finalized")
    if Path(str(evidence.get("transcript", ""))).resolve() != transcript.resolve():
        fail(errors, "smoke evidence transcript path does not match transcript artifact")
    verify_memory_fields(errors, memory, transcript, metadata, "smoke evidence")


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    gh_log = Path(metadata["gh_log"])
    fresh_eyes_log = Path(metadata["fresh_eyes_log"])
    state_dir = Path(metadata["state_dir"])
    branch = metadata["branch"]
    repo = Path(metadata["repo"])
    origin = Path(metadata["origin"])

    if not gh_log.exists():
        fail(errors, f"missing mock gh log: {gh_log}")
        gh_text = ""
    else:
        gh_text = gh_log.read_text(encoding="utf-8", errors="replace")

    gh_lines = gh_text.splitlines()
    pr_create_lines = [line for line in gh_lines if "gh pr create" in line]
    if not pr_create_lines:
        fail(errors, "mock gh did not record `gh pr create`")
    fresh_eyes_events = [i for i, line in enumerate(gh_lines) if "fresh_eyes.command invoked" in line]
    pr_create_events = [i for i, line in enumerate(gh_lines) if "gh pr create" in line]
    if not fresh_eyes_events:
        fail(errors, "mock event log did not record fresh_eyes.command before PR creation")
    elif pr_create_events and min(fresh_eyes_events) > min(pr_create_events):
        fail(errors, "configured fresh_eyes command ran after PR creation; final check must block handoff")
    for line in pr_create_lines:
        if f"cwd={repo}" not in line:
            fail(errors, f"`gh pr create` did not run from fixture repo cwd: {line}")
        if "--head" not in line:
            fail(errors, "`gh pr create` was called without --head")
        if not re.search(r"--head\s+" + re.escape(branch) + r"(\s|$)", line):
            fail(errors, f"`gh pr create` did not use expected --head {branch!r}: {line}")
        if re.search(r"--title\s+['\"]?none\\?:", line, re.IGNORECASE):
            fail(errors, f"no-ticket PR title incorrectly uses `none:` prefix: {line}")
    if "gh issue " in gh_text:
        fail(errors, "no-ticket smoke called `gh issue`; ticket association was guessed or fetched")
    if not fresh_eyes_log.exists():
        fail(errors, f"configured fresh_eyes command did not run; missing log: {fresh_eyes_log}")
    elif "fresh_eyes.command invoked" not in fresh_eyes_log.read_text(encoding="utf-8", errors="replace"):
        fail(errors, "configured fresh_eyes command log did not contain invocation marker")
    if not (run_dir / "pr-url.txt").exists():
        fail(errors, "fake PR URL was not produced")
    skipped_gate_marker = repo / "workflows-should-skip.marker"
    if skipped_gate_marker.exists():
        fail(errors, f"changed-file gate selection ran a gate that should have been skipped: {skipped_gate_marker}")
    if "workflows_should_skip.py" in gh_text or "workflows-should-skip" in gh_text:
        fail(errors, "mock event log suggests skipped workflow gate ran or was treated as selected")

    pushed = subprocess.run(
        ["git", "--git-dir", str(origin), "show-ref", "--verify", f"refs/heads/{branch}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if pushed.returncode != 0:
        fail(errors, f"expected branch was not pushed to local origin: {branch}")

    transcripts = sorted(state_dir.glob("runs/ready-for-review/*/*/transcript.md"))
    if not transcripts:
        fail(errors, f"no verbose transcript found under {state_dir}/runs/ready-for-review")
    else:
        newest = transcripts[-1]
        text = newest.read_text(encoding="utf-8", errors="replace")
        for label, pattern in REQUIRED_TRANSCRIPT_PATTERNS:
            if not re.search(pattern, text, re.IGNORECASE):
                fail(errors, f"transcript {newest} missing marker: {label}")
        if not re.search(r"no[- ]issue|ticket[_ -]?id\s*[:=]\s*`?none`?|ticket:\s*\{id:\s*\"none\"", text, re.IGNORECASE):
            fail(errors, f"transcript {newest} does not record no-ticket state")
        phase2_entry = re.search(r"phase[- ]2[- ]entry|Phase 2 entered", text, re.IGNORECASE)
        if phase2_entry:
            preload_area = text[:phase2_entry.start()]
            for aux in ["phase-2-gates", "phase-3-review", "phase-4-submit"]:
                if aux not in preload_area:
                    fail(errors, f"transcript {newest} does not show {aux} preloaded before Phase 2")
        if not re.search(r"parallel", text, re.IGNORECASE):
            fail(errors, f"transcript {newest} does not record fast-path parallel/sequential gate mode")
        for prompt_error in duplicate_approval_prompt_errors(text):
            fail(errors, f"transcript {newest} {prompt_error}")
        memory_markers = re.findall(r"kind:\s*ready-for-review-session-memory-v1", text, re.IGNORECASE)
        if len(memory_markers) != 1:
            fail(errors, f"transcript {newest} must record exactly one structured memory marker, found {len(memory_markers)}")
        transcript_memory = extract_transcript_memory(text)
        if not transcript_memory:
            fail(errors, f"transcript {newest} missing parseable structured memory JSON block")
        else:
            verify_memory_fields(errors, transcript_memory, newest, metadata, "transcript")
        if "--head" not in text and "--head" not in gh_text:
            fail(errors, f"neither transcript {newest} nor mock gh log records explicit --head PR creation")
        verify_evidence_json(errors, newest, metadata)

    return errors


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-ready-for-review-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        state = run_dir / "state"
        log = run_dir / "gh.log"
        metadata = {
            "run_dir": str(run_dir),
            "repo": str(run_dir / "repo"),
            "state_dir": str(state),
            "gh_log": str(log),
            "fresh_eyes_log": str(run_dir / "fresh-eyes.log"),
            "origin": str(run_dir / "origin.git"),
            "branch": "agent-smoke/no-ticket-verbose",
            "base": "main",
        }
        write(run_dir / "metadata.json", json.dumps(metadata))
        repo = run_dir / "repo"
        subprocess.run(["git", "init", "--bare", str(run_dir / "origin.git")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(["git", "init", str(repo)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(["git", "config", "user.email", "selftest@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Self Test"], cwd=repo, check=True)
        write(repo / "README.md", "self-test\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "self test"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(["git", "branch", "-M", "agent-smoke/no-ticket-verbose"], cwd=repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(run_dir / "origin.git")], cwd=repo, check=True)
        subprocess.run(["git", "push", "origin", "agent-smoke/no-ticket-verbose"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        write(log, f"2026-01-01T00:00:00Z\tcwd={repo}\tgh pr view\nfresh_eyes.command invoked\n2026-01-01T00:00:01Z\tcwd={repo}\tgh pr create --head agent-smoke/no-ticket-verbose --title Smoke\n")
        write(run_dir / "pr-url.txt", "https://example.invalid/beislid-smoke/pull/1\n")
        write(run_dir / "fresh-eyes.log", "fresh_eyes.command invoked\n")
        transcript = state / "runs" / "ready-for-review" / "abc123" / "20260101T000000Z" / "transcript.md"
        write(transcript, """# ready-for-review verbose transcript
phase-1-detect
phase-2-gates
phase-3-review
phase-4-submit
phase 1 entry
phase 2 entry
phase 3 entry
phase 4 entry
fast-path eligible
parallel safe gate validate-fixture
parallel safe gate validate-skills-area
selected gate validate-fixture from gate_sets selector docs-files
selected gate validate-skills-area from gate_sets selector skill-files
skipped gate workflows-should-skip selector workflow-files no changed files matched
combined review/final-check complete
ok: fixture validated
ticket_id: `none`
git push completed
PR opened at https://example.invalid/beislid-smoke/pull/1
--head
kind: ready-for-review-session-memory-v1
```json
{
  "kind": "ready-for-review-session-memory-v1",
  "branch": "agent-smoke/no-ticket-verbose",
  "base": "main",
  "ticket": {"id": "none", "title": "none", "url": ""},
  "pr": {"url": "https://example.invalid/beislid-smoke/pull/1", "title": "Smoke", "base": "main"},
  "phase_path": "new-pr-fast-path",
  "evidence": {
    "loaded_aux_files": ["phase-1-detect", "phase-2-gates", "phase-3-review", "phase-4-submit"],
    "transcript": "TRANSCRIPT_PLACEHOLDER",
    "gates": "parallel validate-fixture ok",
    "review": "combined review/final-check complete"
  }
}
```
""".replace("TRANSCRIPT_PLACEHOLDER", str(transcript)))
        write(transcript.parent / "evidence.json", json.dumps({
            "kind": "ready-for-review-smoke-evidence-v1",
            "repo": str(repo),
            "branch": "agent-smoke/no-ticket-verbose",
            "base": "main",
            "ticket_id": "none",
            "transcript": str(transcript),
            "finalized": True,
            "memory": {
                "kind": "ready-for-review-session-memory-v1",
                "branch": "agent-smoke/no-ticket-verbose",
                "base": "main",
                "ticket": {"id": "none", "title": "none", "url": ""},
                "pr": {"url": "https://example.invalid/beislid-smoke/pull/1", "title": "Smoke", "base": "main"},
                "phase_path": "new-pr-fast-path",
                "evidence": {
                    "loaded_aux_files": REQUIRED_LOADED_AUX,
                    "transcript": str(transcript),
                    "gates": "parallel validate-fixture ok",
                    "review": "combined review/final-check complete",
                },
            },
        }))
        duplicate_prompt_errors = duplicate_approval_prompt_errors("""
Approve pushing `agent-smoke/no-ticket-verbose` and creating this PR against `main`?
Approve pushing and creating the PR with the title/body above?
""")
        if not duplicate_prompt_errors:
            print("self-test failed:", file=sys.stderr)
            print("- duplicate approval prompt guard did not detect duplicated PR prompts", file=sys.stderr)
            return 1

        errors = verify(run_dir)
        if errors:
            print("self-test failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("ok: verify self-test passed")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?", help="Run directory printed by setup.py")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.run_dir:
        parser.error("run_dir is required unless --self-test is used")
    errors = verify(Path(args.run_dir).resolve())
    if errors:
        print("ready-for-review smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: ready-for-review agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
