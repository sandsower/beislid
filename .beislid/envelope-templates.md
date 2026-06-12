# Beislið envelope — output templates

Envelope-specific copy: orientation, step one-liners, verdict prompts, refusal messages, and terminal states. Loaded from `skills/envelope/SKILL.md` through the per-skill auxiliary symlink. Shared primitives live in `output-templates.md`.

## Orientation

≤240 chars:

```
📦 Envelope session for `<input>` on `<branch>`. I'll author execution envelopes, take per-envelope verdicts, and export an approved bundle to `.beislid/exports/`. Cache: <fresh|stale|cold>.
```

## Step one-liners

Entry:

```
🔄 Step 1: Intake — resolving input and planning context.
🔄 Step 2: Author — drafting one execution envelope per AFK-ready slice.
🔄 Step 3: Approve — collecting per-envelope verdicts.
🔄 Step 4: Export — writing, validating, and committing the bundle.
🔄 Step 5: Revise — re-authoring bundle `<id>` v<N+1> from feedback.
```

Exit:

```
✓ Step 1: Intake resolved — <ticket|contract-file> → <N> candidate slices, bundle-id `<id>`.
✓ Step 2: Authored <N> draft envelopes.
✓ Step 3: Verdicts — <A> approved, <R> rejected, <D> demoted to HITL.
✓ Step 4: Bundle `<id>` exported and validated; checkpoint <written|skipped>; commit <done|declined|printed>.
✓ Step 5: Bundle `<id>` v<N+1> exported (supersedes <hash-prefix>…); <A> re-approved, <C> carried forward.
```

## Revision-mode entry

When intake detects a manifest/bundle with pause/review feedback (delivery artifact or bundle status):

```
🔁 Revision mode: bundle `<bundle-id>` v<N> carries feedback — <one-line summary>. I'll re-author the affected envelopes, take delta verdicts, and re-export v<N+1> in place superseding the prior bundle by hash.
```

## Nothing-to-revise refusal

When intake input is an export manifest or bundle with `status: approved` and no pause/review feedback:

```
⛔ This manifest's bundle is `status: approved` with no pause or review feedback — nothing to revise; nothing was changed. Re-run /envelope with a ticket or contract to author new work, or point me at the delivery feedback artifact to revise this bundle.
```

## Bundle collision

```
⛔ `.beislid/exports/<bundle-id>/` already exists. Overwriting would corrupt the supersede chain for downstream runners. Choose a different bundle-id, or delete the directory deliberately and re-run.
```

## Verdict prompt (per envelope, one sitting)

```
Envelope <i>/<N>: `<slice-id>` — <objective one-liner>
Verdict? (a) approve for AFK export, (r) reject (drop from bundle), (d) demote to HITL (keep interactive, not exported).
```

Rejections and demotions never block the rest of the batch.

## Zero-AFK terminal state

```
💭 No envelopes were approved for AFK export — nothing to export (fail-closed: no bundle, no checkpoint, no commit).
Verdict summary: <per-slice verdict + rationale>.
Recommended next step: run `kickoff` on this branch for the interactive (HITL) path.
```

## Validation failure

```
⚠️ `beislid export validate` failed for `<bundle-dir>`:
<validator errors verbatim>
The bundle was not checkpointed or committed. Fix the listed fields and re-export; do not bypass the validator.
```

## Post-export guidance

```
✅ Bundle `<bundle-id>` exported, validated, and <committed|ready to commit>.
Fresh-session execution: `rondo run-once --manifest .beislid/exports/<bundle-id>/slices/<slice-id>.json`
This is a safe boundary to run `/clear` or `/new`; the export manifest doubles as the checkpoint payload.
```

## Char budgets

- Orientation: ≤240 chars.
- Step one-liners: ≤120 chars.
- Refusal/terminal messages: ≤700 chars.
