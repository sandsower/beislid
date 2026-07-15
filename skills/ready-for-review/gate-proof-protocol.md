# exact gate proof reuse protocol v1

Load this file only when at least one selected computational gate declares `evidence_reuse.mode: exact`.
If this file or the `beislid gate-proof` command is unavailable, warn and run every selected gate normally.

## Eligibility

Normalize absent `mutates` to `false` before building a request.
Only a computational sensor with `mutates: false` and `evidence_reuse.mode: exact` is eligible.
Never consult reusable proof while running the required clean evaluator.

## Request

Write a scratch JSON file under the active run artifacts when possible, otherwise use a temporary file and remove it after the phase.
Use this shape:

```json
{
  "kind": "gate-proof-request-v1",
  "gate": {
    "name": "full-tests",
    "scope": "repo",
    "cwd": ".",
    "command": "python3 -m pytest",
    "mutates": false,
    "evidence_reuse": {
      "mode": "exact",
      "environment": {
        "variables": ["CI"],
        "commands": [["python3", "--version"]]
      }
    }
  },
  "selection": {"base": "origin/main"}
}
```

Use the normalized gate fields and Phase 1 base exactly.
Never add environment inputs inferred from the current process.
Only configured variable names and argv-style commands belong in the request.

## Lookup

Run:

```bash
beislid gate-proof lookup --request-file <request.json>
```

Accept reuse only when the command succeeds, `kind` is exactly `gate-proof-decision-v1`, `decision` is `reuse`, and `reason` is `exact_match`.
Every other output or failure means normal gate execution without a user prompt.

Record a reused gate as passing with its proof key, proof path, and source run.
Say that evidence was reused, not that the command ran in the current phase.
Remove reused gates from fast-path execution batches.

## Recording a new proof

Run the gate through the existing path and build the normal immutable gate result envelope first.
When a run ledger is active, add the proof request to the existing recording command:

```bash
beislid run-ledger gate --run-id <run_id> --flow <flow> --name <gate> --scope <scope> --envelope-file <envelope.json> --proof-request-file <request.json>
```

Treat a returned proof status of `skipped` as non-blocking because the normal gate envelope remains authoritative.
Without an active run ledger, keep the normal envelope and do not create reusable proof state.

## Invariants

- Missing, stale, malformed, dirty, mutating, or ambiguous proof state runs the gate normally.
- Failed, skipped, or error gate envelopes never populate proof state.
- Missing or changed source artifacts invalidate a stored proof.
- Exact computational proof never replaces clean evaluation, inferential review, or human proof.
