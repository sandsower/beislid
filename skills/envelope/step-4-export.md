# envelope step 4 export v1

Authoritative JIT protocol for envelope Step 4. Load only with ≥1 approved envelope from Step 3.

## Purpose

Write, validate, checkpoint, and commit the bundle. Everything here is deterministic; no new decisions.

## Protocol

Print the Step 4 entry one-liner from `envelope-templates.md`.

### Write the bundle

Evaluate action policy for `export.bundle.write` (`workspace-write`). Re-check the collision tripwire (non-revision; revision mode rewrites in place), then write `.beislid/exports/<bundle-id>/` per `docs/configuration.md`:

- `bundle.json` — `approved-slice-plan-export-v0`: `kind`, `version` (1 first export; prior+1 revision), `status: approved`, `supersedes` (`null` first export; prior bundle sha for revisions), `generated_from`, `source_work_contract`, `slice_plan` (incl. Step 2 `parallel_groups`), approved `children` with `source_ticket` when known, `dependency_graph` across exported batch slices, `proof_requirements`, `guides_and_gates`, `approval`, `runner_extensions`, `validation` (`schema_version`, judged `rubric_version`, default `afk-rubric-v1`, `notes`), `ownership`.
- `slices/<slice-id>.json` — `approved-slice-v1`: `schema`, `slice_id`, `prompt`, `boundaries`, `dependencies`, `proof_requirements`, `command_proofs` (when drafted; distinct RON-146 executable exit-code proofs, see `docs/configuration.md` "Command Proofs v0" — absent/empty is valid, never a validation error), `output_expectations`, `parent_contract`, `repo`, `allowed_actions`, `process_provider`, and when tiered, `runner_extensions.model_routing` exports a generic boundary list under `routing` (`planning`, `implementation`, `review_fix`, `gate_repair`) plus the collapsed compatibility projection `tier`, `mode`, and `candidates` resolved from `model_routing.tiers`.
- `slices/<slice-id>.md` — human summary: source/approval, objective, scope, autonomy, proof, pause conditions, delivery, ownership.

### Validate (fail-closed)

Run `beislid export validate .beislid/exports/<bundle-id>`. On failure, print the validation-failure copy plus errors verbatim, fix, re-export, re-validate. Never checkpoint/commit an unvalidated bundle.

### Checkpoint

Evaluate action policy for `checkpoint.envelope_exported` with class `workspace-write`. Update `.beislid/checkpoints/latest.json` with a replaceable latest-pointer entry: event `envelope_exported`, path to the bundle's `bundle.json`, `ticket: {id, title}` when known, branch, source skill `envelope`, timestamp. The export manifest doubles as the checkpoint payload. Pointer failures are reported but do not undo the export.

### Commit

Exports are repo-committed by default so provenance travels with the code. Evaluate action policy for `git.commit` (local git mutation); on `ask`, show the file list and proposed message (`Export envelope bundle <bundle-id> (<ticket-id>)`). On approval, stage only the bundle directory and commit. The checkpoint pointer stays local (gitignored per-machine state); the committed bundle carries the durable boundary payload. On decline or `deny`, print the exact `git add`/`git commit` commands for manual use. Push and PR creation are out of scope.

Generic boundary rules are the runtime contract; the compatibility projection only exists for runners that still need a single collapsed route.

### Hand off

Print the post-export guidance from `envelope-templates.md`, including the exact `rondo run-once --manifest` invocation per slice. Finalize the run ledger with bundle path, validator evidence, verdicts, and commit status when active.

## Exit

Print the Step 4 exit one-liner. Required outputs: bundle path, validator result, checkpoint status, commit status, per-slice run commands.

## Tripwires

- Validator exit 0 is a precondition for checkpoint and commit, not a parallel step.
- Stage only the export bundle; the checkpoint pointer stays local and unrelated changes never ride along.
- Do not push, open PRs, or start executing slices.
