# Work Contract examples

These are compact, human-readable examples of `work-contract-v1` in use. They
show scope classification, proof requirements, and the approval boundary for a
few common shapes. They do **not** authorize automatic execution before human
approval.

For the reserved `slice_plan` / `children` slots, keep the current v1 defaults
unless a downstream slice-planning workflow has explicitly approved them.
When child slices matter, the examples below sketch them separately so the
contract remains readable.

## Quick map

| Shape | Scope kind | Typical route | Typical proof |
|---|---|---|---|
| Atomic bugfix | `atomic` | `blueprint` | one `command_gate` |
| Small feature | `single_pr` | `blueprint` | `command_gate` + review-ready evidence |
| Multi-slice feature | `multi_slice` | `break_spec` | `command_gate` + human approval |
| Migration | `project` | `spec_refinement` | dry run + human approval |
| New project bootstrap | `project` | `spec_refinement` | setup artifact + command gate |
| Review-response batch | `multi_slice` | `break_spec` or `blueprint` | review evidence + targeted gates |

## 1) Atomic bugfix

# Work Contract: Fix a broken docs link

Kind: work-contract-v1
Status: approved

## Source
- Type: Linear issue
- Identifier: BEI-13
- URL: https://linear.app/teotl/issue/BEI-13/gh-61-p2-add-work-contract-examples-and-setup-templates

## Problem
A single stale cross-reference points readers at the wrong setup guidance.

## Desired Outcome
The link resolves to the intended docs page and no unrelated workflow policy changes.

## Constraints
- Keep the change in one PR.
- No tracker or gate behavior changes.
- No automatic execution before approval.

## Acceptance Outcomes
- The broken link is corrected.
- The target file still renders cleanly.
- The diff stays within the scoped docs file(s).

## Unknowns / Human Decisions
- None blocking.

## Risk Classification
- Low — one localized docs fix.

## Extension Slots
```yaml
scope_classification:
  kind: atomic
  confidence: high
  rationale: "One localized correction with a single review path."
  recommended_route: blueprint
  requires_human_approval: false
  requires_split: false
  split_reason: null

proof_requirements:
  - kind: proof-requirement-v1
    id: docs-link-check
    type: command_gate
    stage: pre-pr
    status: required
    success_criteria:
      - "Docs link check passes for the touched file."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: gate_envelope
      reference: "command transcript or run-ledger gate path"

slice_plan: null
children: []
```

## Expected output
- Route: `blueprint`
- Proof: one local command gate
- Approval stop: unchanged; no execution before review

## 2) Small feature

# Work Contract: Add a reusable setup note for tracker/review choices

Kind: work-contract-v1
Status: approved

## Source
- Type: Linear issue
- Identifier: BEI-13
- URL: https://linear.app/teotl/issue/BEI-13/gh-61-p2-add-work-contract-examples-and-setup-templates

## Problem
New users need a short, reusable explanation for choosing tracker and PR-review policy.

## Desired Outcome
A single docs addition explains the most common setup choices without expanding workflow scope.

## Constraints
- Keep the feature in one PR.
- Reuse existing workflow concepts and names.
- Avoid implying unattended execution.

## Acceptance Outcomes
- The new note is short and readable.
- It explains when to pick each policy shape.
- It keeps setup guidance distinct from approval semantics.

## Unknowns / Human Decisions
- Which entry point should link to it first.

## Risk Classification
- Medium — small, but it affects first-run guidance.

## Extension Slots
```yaml
scope_classification:
  kind: single_pr
  confidence: high
  rationale: "One coherent docs feature with a single review path."
  recommended_route: blueprint
  requires_human_approval: false
  requires_split: false
  split_reason: null

proof_requirements:
  - kind: proof-requirement-v1
    id: docs-drift-check
    type: docs_drift_check
    stage: pre-pr
    status: advisory
    success_criteria:
      - "The new note matches current workflow guidance."
    failure_policy:
      on_missing: warn
      on_failure: warn
      retryable: false
    expected_artifact:
      kind: note
      reference: "linked docs page or short review note"

slice_plan: null
children: []
```

## Expected output
- Route: `blueprint`
- Proof: one small docs check plus reviewable copy
- Approval stop: still required before any broader setup change

## 3) Multi-slice feature

# Work Contract: Add Work Contract examples and setup templates

Kind: work-contract-v1
Status: approved

## Source
- Type: Linear issue
- Identifier: BEI-13
- URL: https://linear.app/teotl/issue/BEI-13/gh-61-p2-add-work-contract-examples-and-setup-templates

## Problem
Work Contracts, proof requirements, and child slices are hard to learn without examples across work sizes.

## Desired Outcome
Readers can copy a short contract example, see the scope classification, and understand which proof is required before moving on.

## Constraints
- Keep Beislið semantics explicit.
- Do not frame any example as automatic execution.
- Keep examples short and readable.

## Acceptance Outcomes
- Examples cover atomic, single-PR, multi-slice, migration, bootstrap, and review-response batch shapes.
- Each example shows scope classification and proof requirements.
- Setup guidance stays separate from execution semantics.

## Unknowns / Human Decisions
- How much of the setup guidance belongs in a dedicated page versus the rollout guide.

## Risk Classification
- Medium — the patch spans multiple docs surfaces.

## Extension Slots
```yaml
scope_classification:
  kind: multi_slice
  confidence: high
  rationale: "The requested doc set naturally splits into multiple short, independently useful slices."
  recommended_route: break_spec
  requires_human_approval: true
  requires_split: true
  split_reason: "Examples and setup templates are distinct docs with separate entry points."

proof_requirements:
  - kind: proof-requirement-v1
    id: docs-drift-check
    type: docs_drift_check
    stage: pre-pr
    status: required
    success_criteria:
      - "The new docs and links match the current workflow guidance."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: gate_envelope
      reference: "command transcript or run-ledger gate path"
  - kind: proof-requirement-v1
    id: human-approval
    type: human_approval
    stage: pre-pr
    status: required
    success_criteria:
      - "A human has approved the example scope and routing."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: false
    expected_artifact:
      kind: approval_note
      reference: "approved review or planning comment"

slice_plan: null
children: []
```

## Child slice sketch

- `docs/work-contract-examples.md` — short contract examples across the six requested shapes.
- `docs/setup-templates.md` — copyable starter policy patterns.
- `docs/how-to-use.md` / `docs/team-rollout.md` — entry-point links.

## Expected output
- Route: `break-spec`
- Proof: docs drift check plus human approval
- Approval stop: yes; the split is explicit and reviewable

## 4) Migration

# Work Contract: Migrate legacy setup snippets to typed fenced blocks

Kind: work-contract-v1
Status: approved

## Source
- Type: Linear issue
- Identifier: BEI-13
- URL: https://linear.app/teotl/issue/BEI-13/gh-61-p2-add-work-contract-examples-and-setup-templates

## Problem
Older docs snippets can drift from the canonical typed-fence grammar.

## Desired Outcome
The docs use the current block syntax consistently and readers can migrate their configs without guessing.

## Constraints
- Preserve the meaning of existing examples.
- Keep the conversion manual-reviewable.
- Do not treat the migration as a runtime change.

## Acceptance Outcomes
- All touched snippets use current typed fences.
- The migration story includes a dry run or validation step.
- The docs explain what changed and why.

## Unknowns / Human Decisions
- Whether to keep a legacy snippet as a historical note.

## Risk Classification
- High — a migration across multiple docs surfaces can mislead setup.

## Extension Slots
```yaml
scope_classification:
  kind: project
  confidence: high
  rationale: "The migration spans multiple docs and needs a clear boundary before slice execution."
  recommended_route: spec_refinement
  requires_human_approval: true
  requires_split: true
  split_reason: "The migration may need separate slices for examples, rollout text, and config references."

proof_requirements:
  - kind: proof-requirement-v1
    id: migration-dry-run
    type: migration_dry_run
    stage: pre-pr
    status: required
    success_criteria:
      - "A dry run shows the converted docs still validate."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: dry_run_log
      reference: "validation transcript or migration note"
  - kind: proof-requirement-v1
    id: human-approval
    type: human_approval
    stage: pre-pr
    status: required
    success_criteria:
      - "A human has approved the migration boundary."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: false
    expected_artifact:
      kind: approval_note
      reference: "approved review or planning comment"

slice_plan: null
children: []
```

## Child slice sketch

- `docs/examples/README.md` — update the example index.
- `docs/workflow-authoring.md` — point to the new templates.
- `docs/configuration.md` — keep the canonical reference link up to date.

## Expected output
- Route: `spec_refinement` first, then slice planning if needed
- Proof: dry run plus approval
- Approval stop: yes; migration boundaries must be explicit

## 5) New project bootstrap

# Work Contract: Bootstrap a fresh repo with the minimum Beislið workflow

Kind: work-contract-v1
Status: approved

## Source
- Type: Linear issue
- Identifier: BEI-13
- URL: https://linear.app/teotl/issue/BEI-13/gh-61-p2-add-work-contract-examples-and-setup-templates

## Problem
A new repo needs a smallest-useful Beislið starting point before the team adds stricter policy.

## Desired Outcome
A fresh repository can adopt the minimum workflow, audit it, and then layer in stricter gates only when ready.

## Constraints
- Keep the first pass small.
- Prefer a single starter config over a broad rollout.
- Do not imply babysit or PR automation is required on day one.

## Acceptance Outcomes
- The starter config includes the version stamp and ticket source strategy.
- `/doctor` can audit the result.
- The docs explain the next escalation steps.

## Unknowns / Human Decisions
- Which optional integrations the new repo wants first.

## Risk Classification
- Medium — broad enough to affect team rollout, but still a starter.

## Extension Slots
```yaml
scope_classification:
  kind: project
  confidence: high
  rationale: "A bootstrap is a broad starting point that should stay in spec refinement until the team chooses its starter policy."
  recommended_route: spec_refinement
  requires_human_approval: true
  requires_split: false
  split_reason: null

proof_requirements:
  - kind: proof-requirement-v1
    id: starter-config-exists
    type: artifact_exists
    stage: pre-pr
    status: required
    success_criteria:
      - "The starter workflow file exists and is readable."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: false
    expected_artifact:
      kind: file_path
      reference: ".beislid/workflow.md"
  - kind: proof-requirement-v1
    id: doctor-audit
    type: command_gate
    stage: pre-pr
    status: required
    success_criteria:
      - "Doctor validates the new starter config."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: gate_envelope
      reference: "doctor audit summary or transcript"

slice_plan: null
children: []
```

## Child slice sketch

- `docs/team-rollout.md` — minimum viable rollout path.
- `docs/setup-templates.md` — starter policy patterns.
- `docs/examples/07-manual-no-tracker.md` — fully manual baseline.

## Expected output
- Route: `spec_refinement`
- Proof: starter config exists + doctor audit
- Approval stop: yes; bootstrap policy should be explicit before rollout

## 6) Review-response feedback batch

# Work Contract: Batch a set of review comments into separate follow-ups

Kind: work-contract-v1
Status: approved

## Source
- Type: Linear issue
- Identifier: BEI-13
- URL: https://linear.app/teotl/issue/BEI-13/gh-61-p2-add-work-contract-examples-and-setup-templates

## Problem
A review-response pass may include several unrelated comments that should not all be handled by the same slice.

## Desired Outcome
The response plan separates in-scope fixes from out-of-scope follow-ups and keeps the reply path explicit.

## Constraints
- Keep reply intent tied to the source review.
- Create follow-up items for anything that should not land in the same patch.
- Do not push changes until the response is clear.

## Acceptance Outcomes
- Each actionable review item is categorized.
- Out-of-scope follow-ups become child tickets or slices.
- The response text remains concise and evidence-based.

## Unknowns / Human Decisions
- Which review items are accepted versus pushed back.

## Risk Classification
- Medium — a batch can expand quickly if the feedback is not separated early.

## Extension Slots
```yaml
scope_classification:
  kind: multi_slice
  confidence: medium
  rationale: "One feedback batch can split cleanly into fixable comments and follow-up items."
  recommended_route: break_spec
  requires_human_approval: true
  requires_split: true
  split_reason: "Review feedback often needs separate fixes, replies, and follow-up tickets."

proof_requirements:
  - kind: proof-requirement-v1
    id: review-evidence
    type: review
    stage: pre-pr
    status: required
    success_criteria:
      - "The review feedback is categorized and addressed or pushed back with evidence."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: review_note
      reference: "review-response draft or reply summary"
  - kind: proof-requirement-v1
    id: targeted-gate
    type: command_gate
    stage: pre-pr
    status: required
    success_criteria:
      - "The chosen fix path passes its targeted validation."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: gate_envelope
      reference: "command transcript or run-ledger gate path"

slice_plan: null
children: []
```

## Child slice sketch

- `fix-in-scope-comments` — patch the comments that belong in the same PR.
- `reply-or-push-back` — write concise evidence-backed responses.
- `follow-up-issues` — create child tickets for the rest.

## Expected output
- Route: `break-spec` or `blueprint`, depending on how many fixes stay together
- Proof: review evidence plus a targeted gate
- Approval stop: yes; replies and fixes should be separated before push
