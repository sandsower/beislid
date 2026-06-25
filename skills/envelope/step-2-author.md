# envelope step 2 author v1

JIT protocol for envelope Step 2. Load after intake approves context and candidate slices.

## Purpose

Draft one self-contained `execution-envelope-v0` (see `docs/configuration.md`) per AFK-candidate slice.

## Protocol

Print the Step 2 entry one-liner from `envelope-templates.md`.

For each candidate slice, draft an envelope with:

- **objective** — the observable slice outcome, not the project goal.
- **slice** — id, include/exclude scope grounded in explored repo evidence.
- **autonomy** — explicit `allow` / `ask` / `deny`; `deny` includes rationale.
- **proof_requirements** — `proof-requirement-v1` from workflow.md gates (`command_gate`) plus slice proof.
- **pause_conditions** — failed proof, ambiguity, unsafe side effects, missing deps, scope drift.
- **dependencies** — inputs, branches, fixtures, tools, upstream slices.
- **expected_delivery** — summary, artifacts (`changed_files`, `proof_results`), next step.
- **tier** — tier + rationale: docs/config `light`; single-module code+tests `standard`; cross-module/design-bearing `heavy`, or demote. Default `prefer`; export resolves `model_routing.tiers`.

### Self-contained prompt

Each exportable `prompt` uses this runner-facing template:

```
## Objective
## Design summary        # decisions from this session that bind the slice
## File scope            # include / exclude
## Constraints           # deny rationale, ownership boundaries
## Verification          # exact commands that prove the slice done
```

Boundaries, dependencies, and proof requirements live in manifest fields; don't duplicate them as prose.

### Cross-ticket dependencies (REQUIRED for batches)

For multi-ticket bundles, record what each producer emits (module/schema/API/fixture), probe suspected cross-ticket consumers, then write explicit edges (consumer depends on producer) and parallel groups for mutually independent slices. Unverified cross-ticket edges demote the consumer to HITL.

### Mechanical fields

- **repo pin** — `repo: {url, base_ref, base_sha}` from origin URL, target branch, and base commit.
- **autonomy mapping** — `allowed_actions: {run_mode, allow, ask, deny}` verbatim; default `run_mode: supervised-auto`.
- **process_provider** — default `{name: claude_code}`; approval may override per slice.
- **AFK eligibility** — judge against rubric (`rubric_path` override, else `afk-rubric.md`); record `rubric_version` (default `afk-rubric-v1`) and evidence.
- **step_hints** — optional ordered phase hints when a slice or its upstream planning context needs different tiers across internal phases; normalize them from the workflow config into exported `runner_extensions.model_routing.step_hints` records with `skill`, `step`, `tier`, `mode`, `rationale`, and resolved `candidates`.

### Probe-evidence gate (hard)

Before approval, probe every cited claim in-session:

- **Gate commands** — run `command -v <first word>`; for repo scripts, `test -f <path>` and probe the interpreter.
- **Include paths** — every scoped path explored, not assumed from filenames.
- **Dependencies** — each resolved to a real path/ref/tool or upstream slice.

Record evidence inline (probe → result). Any unverifiable claim auto-marks **demote-to-HITL**; do not author it as AFK.

Present each draft in the human-readable rendering from `docs/configuration.md`.

## Exit

Print the Step 2 exit one-liner. Required outputs: N drafts, tier+rationale, eligibility notes, pre-marked demotions, and for batches, dependency edges + parallel groups with evidence.

## Tripwires

- No envelope cites a gate command, path, or dependency that was not probed in this session; unverified means demote-to-HITL, never AFK.
- Prompts must be self-contained; "see the ticket" or "as discussed" is a defect.
- Authoring never starts implementation work.
