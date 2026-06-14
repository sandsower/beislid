# envelope step 2 author v1

Authoritative JIT protocol for envelope Step 2. Load after intake has approved planning context and candidate slices.

## Purpose

Draft one self-contained `execution-envelope-v0` (see `docs/configuration.md`) per AFK-candidate slice.

## Protocol

Print the Step 2 entry one-liner from `envelope-templates.md`.

For each candidate slice, draft an envelope with:

- **objective** — the observable slice outcome, not the project goal.
- **slice** — id, include/exclude scope grounded in explored repo evidence.
- **autonomy** — explicit `allow` / `ask` / `deny` lists. `deny` carries rationale so the runner-side agent understands the boundary.
- **proof_requirements** — `proof-requirement-v1` items derived from configured workflow.md gates (gate → `command_gate` mapping) plus slice-specific proof.
- **pause_conditions** — failed required proof, ambiguity, unsafe side effects, missing dependencies, scope drift.
- **dependencies** — required inputs, branches, fixtures, tools, upstream slices.
- **expected_delivery** — summary, artifacts (changed_files, proof_results), next step.
- **tier** — provider-neutral tier + one-line rationale: docs/config-only `light`; single-module code+tests `standard`; cross-module/design-bearing `heavy`, or demote. Default mode `prefer`; export resolves candidates from `model_routing.tiers` (repo override or shipped defaults).

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

### Mechanical fields

- **repo pin** — `repo: {url, base_ref, base_sha}` from `git remote get-url origin`, the target branch, and `git rev-parse` of the base commit at authoring time.
- **autonomy mapping** — `allowed_actions: {run_mode, allow, ask, deny}` carries the envelope lists verbatim; `run_mode` defaults to `supervised-auto` and is confirmed at approval.
- **process_provider** — `{name: claude_code}` default; per-slice override offered at approval.
- **AFK eligibility** — judge against the versioned rubric (`rubric_path` override, else skill `afk-rubric.md`); record `rubric_version` (default `afk-rubric-v1`) and per-criterion evidence.

### Probe-evidence gate (hard)

Before approval, probe every cited claim in-session:

- **Gate commands** — for each cited verification/gate command, run `command -v <first word>`; for repo scripts, `test -f <path>` (and probe the interpreter). Record the probe and result.
- **Include paths** — every path in slice scope explored (listed or read), not assumed from filenames.
- **Dependencies** — each one resolved to a real artifact: existing path/ref/tool, or an upstream slice in the bundle's dependency graph.

Record evidence inline (probe → result). Any unverifiable claim auto-marks **demote-to-HITL**; do not author it as AFK.

Present each draft in the human-readable rendering from `docs/configuration.md`.

## Exit

Print the Step 2 exit one-liner. Required outputs: N draft envelopes with all fields above, tier + rationale per envelope, per-slice eligibility notes, any slices pre-marked for demotion.

## Tripwires

- No envelope cites a gate command, path, or dependency that was not probed in this session; unverified means demote-to-HITL, never AFK.
- Prompts must be self-contained; "see the ticket" or "as discussed" is a defect.
- Authoring never starts implementation work.
