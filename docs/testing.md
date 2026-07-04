# Testing

This repo has three testing layers: a full local CI mirror, individual validators you can run one at a time, and an agent-smoke suite that exercises skills against real hosts.

## Full local CI mirror

`scripts/validate.sh` runs every CI-blocking check from `.github/workflows/validate.yml`, in cheap-first order, and stops at the first failure with a clear per-check banner.

Run it before opening a PR:

```
bash scripts/validate.sh
```

Two checks are warn-skipped rather than failed when the local machine lacks the tool: the `lychee` markdown link check, and `npm test` when `npm` is not on `PATH`.
A warn-skip is reported as a `SKIP:` line during the run and summarized again at the end; it does not affect the script's exit code, but it does mean that check has not actually run locally.
CI always runs the full set, so a warn-skip is not a substitute for CI passing.

## Individual validators

Most checks that `scripts/validate.sh` runs can also be run standalone while iterating on a narrower change:

- `python3 scripts/validate_skills.py` - skill frontmatter lint.
- `python3 scripts/check_skill_size_budgets.py` - hard size caps on prompt-heavy skill files.
- `python3 scripts/check_*_consistency.py` - the eight doc/config consistency checks (artifact templates, contract schema, lifecycle hooks, model routing step hints, planning lifecycle, run ledger skill examples, visual surfaces, workflow signals).
- `bash scripts/test_install.sh` - install.sh integration tests.
- `bash scripts/test_bump_version.sh` - release bump script tests.
- `bash scripts/test_run_ledger.sh` - run ledger utility tests.
- `bash scripts/test_action_policy.sh` / `bash scripts/test_action_policy_protocol.sh` - action policy evaluator tests.
- `bash scripts/test_validate_export.sh` / `bash scripts/test_validate_skills.sh` - validator script tests.
- `python3 scripts/test_workflow_normalizer.py` / `python3 scripts/test_visual_feedback.py` - normalizer and visual feedback tests.
- `python3 scripts/test_agent_smoke_harness.py` - agent-smoke harness self-test only; it mocks every host invocation and runs no live agents.
- `npm test` - show-me integrity tests (Node's built-in test runner).
- `python3 scripts/validate_export.py <bundle-dir>` - validates a single `.beislid/exports/` bundle.

For skill-specific authoring conventions (frontmatter, auxiliary file symlinks, size budgets), see [Skill authoring guide](./skill-authoring.md).

## Agent-smoke suite

`tests/agent-smoke/` runs Beislið skill scenarios against real hosts in isolated fixture repos.
It is local-only: it needs an authenticated host CLI, so it cannot run on GitHub-hosted CI runners.
Current gate host support is Codex.
See [tests/agent-smoke/README.md](../tests/agent-smoke/README.md) for how to run a single scenario, a suite, or the nightly suite (`suites/nightly.json`), which is scheduled locally rather than in CI.
