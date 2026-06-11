# envelope step 4 export v1

Authoritative JIT protocol for envelope Step 4. Load only with ≥1 approved envelope from Step 3.

## Purpose

Write the bundle, validate it mechanically, checkpoint the boundary, and commit. Everything here is deterministic; no new decisions.

## Protocol

Print the Step 4 entry one-liner from `envelope-templates.md`.

### Write the bundle

Evaluate action policy for `export.bundle.write` with class `workspace-write` before writing. Re-check the collision tripwire, then write `.beislid/exports/<bundle-id>/` per the contract in `docs/configuration.md`:

- `bundle.json` — `approved-slice-plan-export-v0`: `kind`, `version` (1 for first export), `status: approved`, `supersedes: null`, `generated_from`, `source_work_contract`, `slice_plan`, `children` (approved slices only), `dependency_graph` (adjacency map, approved slices only), `proof_requirements`, `guides_and_gates`, `approval` (`approved_at`, `approved_by`), `runner_extensions`, `validation` (`schema_version`, `rubric_version: afk-rubric-v0`, `notes`), `ownership`.
- `slices/<slice-id>.json` — `approved-slice-v1` per approved envelope: `schema`, `slice_id`, `prompt` (templated sections from Step 2), `boundaries`, `dependencies`, `proof_requirements`, `output_expectations`, `parent_contract: {id, source: beislid}`, `repo: {url, base_ref, base_sha}`, `allowed_actions: {run_mode, allow, ask, deny}`, `process_provider`, `runner_extensions`.
- `slices/<slice-id>.md` — human-readable summary: source and approval, objective, scope, autonomy, proof, pause conditions, expected delivery, ownership.

### Validate (fail-closed)

Run `beislid export validate .beislid/exports/<bundle-id>`. On exit 0, continue. On failure, print the validation-failure copy from `envelope-templates.md` with the validator errors verbatim, fix the listed fields, re-export, re-validate. Never checkpoint or commit an unvalidated bundle; never bypass the validator.

### Checkpoint

Evaluate action policy for `checkpoint.envelope_exported` with class `workspace-write`. Update `.beislid/checkpoints/latest.json` with a replaceable latest-pointer entry: event `envelope_exported`, path to the bundle's `bundle.json`, `ticket: {id, title}` when known, branch, source skill `envelope`, timestamp. The export manifest doubles as the checkpoint payload; no separate artifact is written. Pointer failures are reported but do not undo the export.

### Commit

Exports are repo-committed by default so provenance travels with the code. Evaluate action policy for `git.commit` (local git mutation); on `ask`, show the file list and proposed message (`Export envelope bundle <bundle-id> (<ticket-id>)`). On approval, stage only the bundle directory and commit. The checkpoint pointer stays local — `.beislid/checkpoints/` is replaceable per-machine convenience state and is conventionally gitignored; the committed bundle itself carries the durable boundary payload. On decline or `deny`, print the exact `git add`/`git commit` commands for manual use. Push and PR creation are out of scope.

### Hand off

Print the post-export guidance from `envelope-templates.md`, including the exact `rondo run-once --manifest` invocation per slice. Finalize the run ledger with bundle path, validator evidence, verdicts, and commit status when active.

## Exit

Print the Step 4 exit one-liner. Required outputs: bundle path, validator result, checkpoint status, commit status, per-slice run commands.

## Tripwires

- Validator exit 0 is a precondition for checkpoint and commit, not a parallel step.
- Stage only the export bundle; the checkpoint pointer stays local and unrelated changes never ride along.
- Do not push, open PRs, or start executing slices.
