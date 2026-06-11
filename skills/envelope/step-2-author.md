# envelope step 2 author v1

Authoritative JIT protocol for envelope Step 2. Load after intake has approved planning context and candidate slices.

## Purpose

Draft one `execution-envelope-v0` (see `docs/configuration.md`) per AFK-candidate slice, complete enough that a fresh session needs nothing else.

## Protocol

Print the Step 2 entry one-liner from `envelope-templates.md`.

For each candidate slice, draft an envelope with:

- **objective** — the observable slice outcome, not the project goal.
- **slice** — id, include/exclude file-and-module scope grounded in the actual repo (explore before claiming; do not scope from filenames alone).
- **autonomy** — explicit `allow` / `ask` / `deny` lists. `deny` carries rationale so the runner-side agent understands the boundary.
- **proof_requirements** — `proof-requirement-v1` items derived from configured workflow.md gates (gate → `command_gate` mapping) plus slice-specific proof.
- **pause_conditions** — failed required proof, ambiguity, unsafe side effects, missing dependencies, scope drift.
- **dependencies** — required inputs, branches, fixtures, tools, upstream slices.
- **expected_delivery** — summary, artifacts (changed_files, proof_results), next step.

### Self-contained prompt

Each slice's exportable `prompt` follows a fixed section template — this is what the runner's agent actually reads:

```
## Objective
## Design summary        # decisions from this session that bind the slice
## File scope            # include / exclude
## Constraints           # deny rationale, ownership boundaries
## Verification          # exact commands that prove the slice done
```

Boundaries, dependencies, and proof requirements go in their dedicated manifest fields (the runner renders those alongside the prompt); do not duplicate them as prose.

### Mechanical fields

- **repo pin** — `repo: {url, base_ref, base_sha}` from `git remote get-url origin`, the target branch, and `git rev-parse` of the base commit at authoring time.
- **autonomy mapping** — `allowed_actions: {run_mode, allow, ask, deny}` carries the envelope lists verbatim; `run_mode` defaults to `supervised-auto` and is confirmed at approval.
- **process_provider** — `{name: claude_code}` default; per-slice override offered at approval.
- **AFK eligibility** — record the eligibility judgment and `rubric_version: afk-rubric-v0` (ticket-embedded criteria; the versioned rubric doc lands in a later phase). A slice whose evidence cannot be verified (named gate command missing, paths unexplored, unresolved dependency) is marked for demotion to HITL rather than authored as AFK.

Present each draft envelope in human-readable form (prose rendering, as in `docs/configuration.md`) so Step 3 verdicts are informed.

## Exit

Print the Step 2 exit one-liner. Required outputs: N draft envelopes with all fields above, per-slice eligibility notes, any slices pre-marked for demotion.

## Tripwires

- No envelope cites a gate command, path, or dependency that was not verified in this session.
- Prompts must be self-contained; "see the ticket" or "as discussed" is a defect.
- Authoring never starts implementation work.
