# ready-for-review phase 3 review v1

Phase 3 is reached only on the normal new-PR path. Existing-PR fast path skips this phase by contract. If this file cannot be read at Phase 3 entry, hard-fail instead of continuing from memory.

## Entry / inputs

Print the Phase 3 entry one-liner from `ready-for-review-templates.md`. In verbose mode, emit the aux-load stamp and phase-entry transcript boundary per the main verbose contract.

Inputs: `base`, full diff against `base`, ticket/spec/design context, Phase 2 gate results and warnings, fast-path state, changed-file/scope mapping for gate reruns, and accumulated user decisions.

## Long-running review policy

Apply this policy to `review`, `fresh-eyes`, and fast-path combined review invocations:

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

1. Make or guide the fix according to normal host behavior.
2. Track findings addressed and risks the user explicitly accepted.
3. If the fix touched functional code, rerun the Phase 2 gates that apply to changed files before continuing. Naming-only, comment-only, or documentation-only fixes do not require rerun unless they affect configured gates.

If rerun gates fail, use Phase 2 failure handling before resuming Phase 3.

The normal review loop converges only when no blocking review findings remain, when remaining Important items are explicitly accepted risks, or when the user explicitly accepts reduced coverage after cancel-and-salvage.

## 3b. Fresh-eyes final pass / fast-path combined review

If `fast_path_eligible=true`, do one combined review instead of separate `review` + `fresh-eyes`: invoke a reviewer with the review contract plus the fresh-eyes whole-diff checklist (cross-file consistency, config drift, stale docs, limits, unused code, baseline compatibility). Label the result `combined review`; it is full coverage for fast-path, not reduced coverage.

Otherwise, after the normal review loop converges, invoke `fresh-eyes` with the full diff against `base`, ticket/spec/design context, verification already run, and review findings fixed or explicitly accepted.

Handle findings with the same severity and long-running policies. Push back on incorrect findings with code/test evidence. If fixes touch functional code, rerun applicable Phase 2 gates before exiting Phase 3.

## Exit / outputs

Phase 3 may exit only when review plus fresh-eyes, or fast-path combined review, has no blocking findings; remaining Important items are explicitly accepted risks; or incomplete/cancelled coverage has explicit reduced-coverage acceptance.

Print the Phase 3 exit one-liner from `ready-for-review-templates.md`, filling `<N>` with findings addressed across review/fresh-eyes or combined review. In verbose mode, append the Phase 3 exit check and transcript boundary.

Outputs to Phase 4: review mode, findings-addressed count, accepted-risk notes, reduced-coverage notes if any, confirmation that no unaccepted blocking findings remain, and confirmation that applicable gates reran after functional review/fresh-eyes/combined-review fixes.

## Phase-local tripwires

- Do not skip `fresh-eyes` after normal review converges on the normal new-PR path; only fast-path may replace it with combined review.
- Do not proceed with Critical findings; Important findings require fixes or explicit user risk acceptance.
- Cancelled/incomplete review requires explicit reduced-coverage acceptance before Phase 4.
