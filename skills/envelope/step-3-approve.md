# envelope step 3 approve v1

Authoritative JIT protocol for envelope Step 3. Load after all draft envelopes are authored.

## Purpose

Collect explicit per-envelope human verdicts in one sitting. Approval is the act that makes export possible; nothing approves itself.

## Protocol

Print the Step 3 entry one-liner from `envelope-templates.md`.

For each draft envelope, show the human-readable rendering and ask the verdict prompt from `envelope-templates.md`:

- **approve** — envelope joins the export set with `status: approved`. Confirm `run_mode` (default `supervised-auto`), `process_provider` (default `claude_code`), and the Step 2 tier + mode (default `prefer`), offering per-slice overrides; a tier override at approval replaces the authored tier and is recorded with the human's rationale.
- **reject** — envelope is dropped from the bundle entirely. Record the reason. Rejection never blocks other envelopes.
- **demote to HITL** — slice stays interactive: excluded from export, recorded in the verdict summary with a recommendation to run it through `kickoff`. Slices pre-marked in Step 2 for unverifiable evidence default to demotion; the human may override only after the evidence gap is closed in-session.

Silence, ambiguity, or skipping is not approval. Every envelope gets an explicit verdict before Step 4.

### Dependency cascade

Dropping a slice (reject or demote) removes it AND its edges from the exported graph. Any remaining slice that depends — directly or transitively — on a dropped slice is itself demoted to HITL: it cannot execute without its dependency. Record the cascade in the verdict summary; export proceeds with the remainder.

### Approval metadata

For each approved envelope record:

- `approved_at` — current UTC timestamp.
- `approved_by` — git identity (`git config user.name` + email when set). The conversation verdict is the approval act; this field is its record.

### Terminal states

- **≥1 approved** — continue to Step 4 with the approved set; rejected/demoted slices appear only in the verdict summary.
- **0 approved** — fail-closed: print the zero-AFK terminal copy from `envelope-templates.md` (no bundle, no checkpoint, no commit) and end the run. Record verdicts in the run ledger when active.

## Exit

Print the Step 3 exit one-liner. Required outputs: verdict per envelope with reasons, approval metadata for approved envelopes, chosen run_mode/process_provider/tier per slice, terminal-state decision.

## Tripwires

- A prior blanket approval ("yes to everything") does not replace per-envelope verdicts; walk each one.
- An exported manifest is an execution affordance — demoted/rejected slices must never reach the bundle.
- Do not edit envelope substance during approval beyond run_mode/provider/tier overrides; substantive changes go back to Step 2.
