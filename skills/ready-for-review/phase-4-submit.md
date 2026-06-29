# ready-for-review phase 4 submit v1

Normal mode loads after Phase 3 has no unaccepted blocking findings; fast-path may preload after Phase 1 but must not enter until Phase 3 passes. Existing-PR fast path never enters.

## Entry contract

Inputs: branch, base, ticket ID/none, diff stats, fast-path state, Phase 2/3 status, clean-eval proof, reduced-coverage acceptance, risks, config, probe state, metadata. Outputs: PR URL/title/base, notes, clean-eval proof, reduced-coverage acceptance, domain-capture status, memory brief status, Phase 4 exit. Main owns cache write-back.

Print entry; emit `working`. Verbose appends transcript events, exit checks.

## Hard gate

Read `approval_gates.pr_title_body` from workflow config. If absent or `prompt`, use explicit-approval path. If `auto`: log title/body to transcript/ledger, record `pr_title_body_approval: auto` with text, emit `working`, proceed to 4c.

**Explicit-approval (default):** Emit `waiting` before PR approval prompt. User must explicitly approve title/body before push/PR. Draft PR creation also needs this. Show title/body as context in progress prose, then ask the single approval question only once in the final/blocking response. Draft-ready after bot fixes needs second explicit approval. Never treat silence, ambiguity, or prior Phase 3 approval as PR approval.

## 4-pre. Paired-set front-load

Before PR side effects, evaluate `domain_expert.agent` ↔ `knowledge_store.path` as one paired set:

- Both configured: `probe(domain_expert.agent)` and `probe(knowledge_store.path)`. If either fails, use the paired-set retry/skip/abort prompt from `ready-for-review-templates.md`.
- Exactly one configured: do not probe; add the paired-half-missing note and treat Phase 4d as disabled.
- Neither configured: do not probe; treat Phase 4d as unconfigured and print disabled note only at 4d.

A session skip suppresses re-check at 4d.

## 4a. Fetch ticket title

If `ticket_id = none`, skip ticket-source probing/fetching. Record `no issue`; PR title must not get a ticket prefix.

If `ticket_source.type: paste`, ask the user for the title while drafting. Otherwise call `probe(ticket_source)` on first need. On failure, use the Phase 4a prompt; proceed-this-session means the user pastes the title manually with no workflow.md change.

On probe success, fetch: `mcp`, `file`, `cli` with `{id}`, or `paste`.

Never infer from issue lists. If discovered incidentally, ask before associating.

## 4b. Draft PR and approval

Compose the proposed PR:

- Title: `<TICKET-ID>: <ticket title>` only when a real ticket id is confirmed; otherwise a concise no-ticket title. Never render `none` as a prefix; `none: <title>` is invalid.
- Base: Phase 1 base.
- Body: Ship summary shape from `artifact-templates.md`: changes, why, proof, warnings, artifacts/follow-ups, ship-time note, deferred-review evidence, accepted risks/reduced coverage.
- Include AI-generated translation notices and a worktree cleanup note when isolated.
- Labels/reviewers only when configured or requested.

If `pr_description.formatter_skill` configured, probe on first need; on failure use Phase 4b prompt + raw draft. No formatter → raw-draft note.

Show final title/body. If `approval_gates.pr_title_body` is `auto`, log to transcript/ledger with `auto` and proceed to 4c without interactive approval. Else wait for explicit approval, and keep the approval question out of progress prose. Never ask twice.

If draft PRs + provider bot review supported, after approval offer draft-bot-review. On yes: create draft, handle bot findings like Phase 3 review, rerun applicable gates after functional fixes, commit/push fixes, ask explicit approval before marking ready (auto path does not apply to draft-ready).

## 4b1. Ship-time planning-artifact summary

If configured, note matching paths from `break_spec_approved`, `spec_approved`, and `blueprint_approved`.

- `remind`: note generated artifacts are present and stay normal repo files.
- `include`: same note plus PR handoff framing.
- `skip`: no extra commentary.
- `clean`: note local-only artifacts are excluded from the shipped handoff surface.

Narration only; no auto-commit/delete/rewrite. Skip when no planning-artifact lifecycle actions exist.

## 4c. Push and create PR

Policy-check push/PR create/draft-ready as `git-remote`; record outcomes. If GitHub/`gh` and `.github/workflows/` changed, preflight `workflow` scope; warn on missing scope. Skip preflight for non-gh providers.

Run from repo cwd with `--head <branch>`; never rely on `gh` upstream inference.

Normal path:

```bash
git push -u origin HEAD
gh pr create --head "<branch>" --title "<title>" --base "<base>" --body "<description>"
```

Draft path adds `--draft`; readying later uses provider command such as `gh pr ready` only after second explicit approval.

On network/sandbox failure, emit `blocked`, surface retry/escalation/abort. Never re-draft or change approved title/body.

Report PR URL with success template. If the provider can report checks, poll/report PR CI once after creation and before final success so the handoff notes capture the initial state. Verbose records push, PR creation, bot-review, fixes, ready-marking, auth preflight.

## 4d. Capture domain knowledge

If 4-pre disabled domain capture, print inline note only.

If configured, decide whether work uncovered durable domain knowledge. Skip purely mechanical work; otherwise spawn `domain_expert.agent` with a concise submitted-work summary and target `knowledge_store.path`. Domain capture is best-effort after PR creation; failure does not invalidate the PR.

## 4e. Structured session memory / memento brief

On successful PR handoff, or on abort after Phase 2 starts or any side effect, complete before final output:

1. If host memory exists or `BEISLID_MEMENTO_CAPTURE=1`, attempt one structured brief.
2. Append/print exactly one literal marker: `kind: ready-for-review-session-memory-v1` with the brief, or `memory brief unavailable:<reason>`.
3. Include repo, branch, base, ticket id/none, PR URL, phase path, aux loaded, transcript path/reason, clean-eval proof, explicit reduced-coverage acceptance, gates incl. parallelism, review/final-check status incl. cancellation/partial output, risks, side effects, host, timestamp, and duration if known.
4. If a run ledger is active: `finalize` only after successful PR handoff; on abort, record `beislid run-ledger interrupt` with context.

Do not finish with only prose such as “brief summarized”; that fails smoke. Do not include secrets, env values, auth headers, or raw stdout/stderr.

## Exit

Emit workflow-signal `done` after successful PR handoff, then print Phase 4 exit. In verbose mode, append exit and loaded/not-reached aux status.

## Phase-local tripwires

- Never push/create/ready a PR without policy and explicit approvals.
- Ticket association is confirmed id or `none`; never guessed from issue lists.
- Always create PRs with explicit repo cwd and `--head <branch>`.
