# ready-for-review phase 3 review v1

Phase 3 is reached only on the normal new-PR path. Existing-PR fast path skips this phase by contract. If this file cannot be read at Phase 3 entry, hard-fail instead of continuing from memory.

## Entry / inputs

Print the Phase 3 entry one-liner from `ready-for-review-templates.md`. In verbose mode, emit the aux-load stamp and phase-entry transcript boundary per the main verbose contract.

Inputs: `base`, full diff against `base`, ticket/spec/design context, Phase 2 gate results and warnings, fast-path state, changed-file/scope mapping for gate reruns, and accumulated user decisions.

## Long-running review policy

Apply this policy to `review`, enabled final checks, and fast-path combined review invocations:

- Announce the review start and that progress will be reported every 60s.
- Poll/report every 60s while the host supports it.
- At 5 minutes, ask: continue waiting, cancel-and-salvage, or abort ready-for-review.
- Never silently skip review coverage; fast-path combined review must be explicit.
- Cancellation is not a pass.

If the user chooses cancel-and-salvage, stop waiting and extract any available partial output from the subagent/tool. Carry usable findings forward by severity; mark unsupported or half-written observations as incomplete. If no partial output is available, say so. Before Phase 4, require explicit reduced-coverage risk acceptance; record it in the transcript, Phase 3 exit summary, memory brief, and PR notes when relevant.

## 3a. Normal review loop

If `fast_path_eligible=true`, skip this subsection and go directly to 3b combined review. Otherwise invoke `review` with the full diff against `base`, ticket/spec/design context, verification already run, and relevant Phase 2 gate results or warnings.

Handle findings by severity:

- Critical findings must be addressed before PR handoff.
- Important findings must be addressed before PR handoff unless the user explicitly accepts the risk.
- Minor findings are optional.

Push back on incorrect findings with code or test evidence. If evidence does not disprove the finding, treat it by severity.

When valid findings require fixes:

1. Policy-check orchestrator-owned writes (`workspace-write` plus known non-read class); fix only on `allow`/approved `ask`.
2. Track findings addressed and risks the user explicitly accepted.
3. If the fix touched functional code, rerun the Phase 2 gates that apply to changed files before continuing. Naming-only, comment-only, or documentation-only fixes do not require rerun unless they affect configured gates.

If rerun gates fail, use Phase 2 failure handling before resuming Phase 3.

The normal review loop converges only when no blocking review findings remain, when remaining Important items are explicitly accepted risks, or when the user explicitly accepts reduced coverage after cancel-and-salvage.

## 3b. Final whole-diff review

Read optional `beislid:fresh_eyes`. Absent/`enabled: true` uses built-in; `enabled: false` is explicit policy. `type: command`: `probe(fresh_eyes.command)`, policy-check classes (`read` unless metadata mutates), then run from repo root with full diff/ticket/spec/design/gate context. Do not rewrite env vars, args, or output paths for ledger storage; record/copy artifacts separately. Treat nonzero/unclear output as blocking unless evidence disproves it.

If `fast_path_eligible=true`, use one combined review: primary review contract plus the selected final whole-diff check. Label built-in mode `combined review`; label custom mode `combined review + fresh_eyes.command`.

Otherwise, after normal review converges, run the selected final check unless disabled. Handle findings with the same severity and long-running policies. If fixes touch functional code, rerun applicable Phase 2 gates before exiting Phase 3.

## Exit / outputs

Phase 3 may exit only when review plus enabled final check, fast-path combined review, or explicit `fresh_eyes.enabled: false` policy has no blocking findings; remaining Important items are accepted risks; or incomplete/cancelled coverage has explicit reduced-coverage acceptance.

Print the Phase 3 exit one-liner from `ready-for-review-templates.md`, filling `<N>` with findings addressed across review/final-check or combined review. In verbose mode, append the Phase 3 exit check and transcript boundary.

Outputs to Phase 4: review mode, final-check mode (`built-in`, `command`, or `disabled-by-workflow`), findings count, accepted/reduced-coverage notes, no unaccepted blockers, and confirmation applicable gates reran after functional review/final-check fixes.

## Phase-local tripwires

- Do not skip policy at covered write/custom commands.
- Do not skip final whole-diff check unless `fresh_eyes.enabled: false`.
- Do not proceed with Critical findings; Important findings require fixes or explicit user risk acceptance.
- Cancelled/incomplete review requires explicit reduced-coverage acceptance before Phase 4.
