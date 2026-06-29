---
name: review-response
description: Use when the user says "review-response", "respond to review", "review comments are back", or "QA sent feedback", or when existing PR review comments or QA feedback need a response. This is the post-review response skill — if someone already reviewed or tested the user's code and left comments, use it. Do NOT use when the user wants to write reviews, start new work (use kickoff), or create a PR (use ready-for-review). Reads project config from `<repo>/.beislid/workflow.md` and probes capabilities lazily as needed.
---

# Review Response

Address post-submission feedback: PR review threads, PR comments, QA ticket comments, and pasted feedback. When fixes belong in an isolated worktree, preserve that worktree context in the response and cleanup notes. See [worktree isolation](../../docs/worktree-isolation.md). Categorize feedback, fix what belongs in scope, draft/print or post replies, run needed gates, and push.

**Don't use this for:** starting new ticket work, creating PRs, or reviewing someone else's PR. Use `kickoff`, `ready-for-review`, or `pr-patrol` instead.

Project config lives at `<repo>/.beislid/workflow.md` (typed-key fenced YAML blocks; format reference at `workflow-md-format.md`). Capabilities are probed lazily on first need per `probe-semantics.md`. Action-risk decisions follow `action-policy-protocol.md`. Output prose follows `output-templates.md` and `review-response-templates.md`.

If the repo declares custom lifecycle hooks, read `../lifecycle-hooks.md` and honor any phase-boundary hooks before and after review-response.

---

## Read workflow.md

Read `<repo>/.beislid/workflow.md`. If it doesn't exist, hard-fail and stop:

> 🛑 No `workflow.md` found in `.beislid/`. If this is a fresh project, run `/setup` to create one. If you moved your config, restore it to `<repo>/.beislid/workflow.md`.

Validate line 1 exactly:

```html
<!-- beislid-workflow: v1 -->
```

If missing or wrong, hard-fail:

> ⚠️ This `workflow.md` is `<found>` but review-response only knows `v1`. Update Beislið or downgrade `workflow.md` by hand to v1 syntax. Review-response will not silently mis-parse.

Compute cache identifiers:

```bash
repo_hash=$(git rev-list --max-parents=0 HEAD | sort | head -c 12)
workflow_hash=$(git hash-object .beislid/workflow.md)
```

Try to read `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/probes/<repo_hash>.json`:

- **Missing** → empty in-memory probe state; cache state `cold`.
- **Present but `workflow_hash` mismatch** → empty in-memory probe state; cache state `stale`.
- **Present and hash matches** → load capability entries; cache state `fresh`. Per-cap freshness uses `probe_cache.ttl_hours` from workflow.md, default 24.

Print orientation prose from `review-response-templates.md` (≤240 chars).

---

## Internal: probe(<cap>)

Reusable lazy-probe contract. Do not re-probe within a run; the in-memory probe state is authoritative.

1. Look up `<cap>` in memory.
2. If present, `status: ok`, and within TTL → return ok; no probe ran.
3. Else run the probe per `probe-semantics.md` for the cap kind. Multi-command CLI capabilities (`pr_review_source`, `pr_review_update`, `ticket_update`) probe as one logical cap by checking every unique binary.
4. On success → return ok.
5. On failure → use call-site-specific prose from `review-response-templates.md`.
6. On `(a)` → re-probe. On `(b)` → mark `session_skip: true` and use the call-site fallback for this session. On `(c)` → abort; do not write cache.

On clean run end, write probed/re-probed entries back to `<repo_hash>.json`, excluding `session_skip`. Preserve doctor-owned fields when present. If workflow.md changed mid-run, do not overwrite stale state; surface the write failure and continue.

---

## JIT phase protocol

Review-response phases are authoritative only after their aux files are read. At each phase boundary, read the matching file and follow it. If a phase file cannot be read, hard-fail instead of continuing from memory.

- Phase 1: `skills/review-response/phase-1-detect.md`
- Phase 2: `skills/review-response/phase-2-fix.md`
- Phase 3: `skills/review-response/phase-3-push.md`

Read `action-policy-protocol.md` before Phase 2/3 side effects. When `BEISLID_VERBOSE=1`, print one aux load stamp after successfully reading each phase file. Stamp format is `✓ review-response/<phase-file-stem> v1 loaded` for `phase-1-detect`, `phase-2-fix`, and `phase-3-push`.

## Checklist

1. **Detect** — read `phase-1-detect.md`. Outputs: ticket/PR identity, selected mode, normalized feedback queue with source metadata.
2. **Categorize and fix** — read `phase-2-fix.md`. Outputs: fix commits or draft-only decisions, reply drafts, change classification, approval state.
3. **Push and reply** — read `phase-3-push.md`. Outputs: gates run/skipped, branch pushed, replies posted/printed, review re-request status.

---

## Phase 1: Detect

Read and follow `phase-1-detect.md`. Print the entry/exit one-liners from `review-response-templates.md`. Do not continue to Phase 2 until feedback is loaded or strict paste fallback has provided enough context.

## Phase 2: Categorize and Fix

Read and follow `phase-2-fix.md`. Print the entry/exit one-liners from `review-response-templates.md`. Do not offer fast path unless every condition in the aux file is met.

## Phase 3: Push, Reply, and Re-request

Read and follow `phase-3-push.md`. Print the entry/exit one-liners from `review-response-templates.md`. Gate, push, and update behavior must use configured workflow.md capabilities and safe temp-file payloads.

---

## Common mistakes

- **Using hidden GitHub reads/writes.** `gh pr view` is allowed only for PR identity detection. PR feedback reads come from `pr_review_source`; PR feedback writes/re-requests come from `pr_review_update`. Otherwise paste/print manually. Evaluate action policy before covered writes.
- **Continuing without feedback context.** Source failure `(b)` means strict paste now, not blind skip.
- **Offering fast path for judgment calls.** Fast path is only for obviously clear fetched feedback with non-manual update paths.
- **Interpolating reply bodies into shell commands.** Use JSON temp files for PR review updates and body/title temp files for ticket updates.
- **Creating child tickets without approval.** Always show title/body and wait for approval.
- **Running from memory after aux read failure.** Restore/reinstall the missing phase file instead.

## Key principles

- **Workflow.md is the source of truth.** One per-project config for kickoff, review-response, and ready-for-review.
- **Lazy probes, not preflight tables.** Probe at first use and narrate failures conversationally.
- **Source metadata matters.** Normalize feedback together, but reply through the correct source/update channel.
- **AFK only inside explicit rails.** Manual/paste sources and ambiguous feedback keep the run human-in-the-loop.
