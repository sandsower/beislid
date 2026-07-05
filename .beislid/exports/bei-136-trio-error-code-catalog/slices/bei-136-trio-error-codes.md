# bei-136-trio-error-codes

Source: BEI-136
Approved: 2026-07-05T23:20:00Z by Vic Valenzuela <victor@dala.care>

## Objective
The deterministic trio ships one frozen error-code contract: action_policy and validate_export emit stable snake_case codes cataloged alongside the 14 normalizer codes in docs/parser-conformance.md.

## Scope
Include:
- `scripts/action_policy.py`
- `scripts/validate_export.py`
- `docs/parser-conformance.md`
- `tests covering the two scripts' error emission (extend existing script harness tests)`

Exclude:
- workflow_normalizer (already cataloged, frozen)
- New conformance corpus cases unless trivial (file follow-up instead)

## Autonomy
- Allow: edit included files, run gates/targeted tests, local commits.
- Ask: scope drift, new dependencies, behavior beyond the bound design.
- Deny: remote writes (push/PR/tracker), external mutations, destructive work outside the repo.

## Proof
- `git diff --check origin/main...HEAD`
- `python3 scripts/check_skill_size_budgets.py`
- `python3 scripts/validate_skills.py`
- `python3 scripts/check_planning_lifecycle_consistency.py`
- `python3 scripts/check_visual_surfaces_consistency.py`
- `python3 scripts/check_artifact_templates_consistency.py`
- `python3 scripts/check_workflow_signals_consistency.py`
- `python3 scripts/check_lifecycle_hooks_consistency.py`
- `python3 scripts/check_run_ledger_skill_examples_consistency.py`

## Pause conditions
Exit-code or message-consumer breakage (grep for downstream parsing of these messages first); any failure class whose meaning is ambiguous.

## Delivery
Both scripts emit '<code>: <message>' with snake_case codes (one per failure class); docs/parser-conformance.md gains two sibling catalog sections in the existing table style, audited against the implementations; olin's port of the two tools has a frozen contract to target.
