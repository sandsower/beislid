# Beislið ready-for-review — output templates

Ready-for-review-specific copy: orientation, per-phase one-liners, probe-failure prompts, capability-disabled notes, PR success prose. Loaded on demand from `skills/ready-for-review/SKILL.md` via the per-skill auxiliary symlink. Shared primitives (12-emoji palette, three-clause shape, char-budget shape, verbose-stamps layout description, inline-note placement) live in `output-templates.md` alongside this file; ready-for-review symlinks both.

## Orientation prose template

Printed once near the top of every ready-for-review run, after reading workflow.md, judging cache freshness, and establishing branch/base/fast-path status (≤240 chars):

```
📋 Preparing `<branch>` against `<base>` for review. Reading `.beislid/workflow.md` (<N>
capabilities configured). Probing lazily as needed. Cache: <fresh|stale|cold>.
```

`<fresh>` — cache file present and `workflow_hash` matches.
`<stale>` — cache file present but `workflow_hash` mismatch; treating as cold this run.
`<cold>` — cache file missing.

If the existing-PR fast path fires, append: ` Existing PR detected — fast-path mode.` If small-diff fast-path fires, append: ` Fast-path eligible.` (still under 240 chars).

## Per-phase one-liners

Each phase prints an entry summary on its way in and an exit summary on its way out. These are status lines, not prompts; continue automatically after green `✓`/`⚡`/`💭` lines unless a documented hard gate, failure, ambiguity, or approval point is reached. At hard approval boundaries, ask the blocking approval question exactly once in user-visible output; context/draft prose must not duplicate the final/blocking prompt. Both stay ≤120 chars. The `🔄` glyph marks the entry; `✓` marks a clean exit; `⚠️` marks an exit with non-blocking findings.

**Phase 1 — Detect:**
```
🔄 Phase 1: Detect — analyzing the diff and probing branch state.
✓ Phase 1: <ticket-id> on `<branch>` → `<base>` (<N> files, <K> lines across <S> scope(s)).
```

**Phase 2 — Quality gates:**
```
🔄 Phase 2: Quality gates — running <N> gate(s) across <S> scope(s).
✓ Phase 2: pre-pr proof satisfied in <duration>; <K> proof item(s) not applicable.
⚡ Phase 2: fast-path ran <N> safe proof gate(s) in parallel; proof satisfied in <duration>.
⚡ Phase 2: clean-eval proof satisfied in <duration>; <N> gate(s) ran on a clean surface.
⚠️ Phase 2: clean-eval failed as <patch-regression|environment_failure>; <summary>.
⚠️ Phase 2: <N> gate(s) needed autofix; resumed after fixes.
```

**Phase 2b — Walkthrough (conditional):**
```
🔄 Phase 2b: Walkthrough — diff exceeds <N>-file threshold; offering walk-the-diff.
✓ Phase 2b: walkthrough done; <K> issues surfaced and addressed.
💭 Phase 2b: skipped at user request.
```

Gate execution failures use the shared Gate result envelope from `output-templates.md`:
```text
⚠️ Gate `<gate-name>` failed: <envelope.summary>.
Failures: <top envelope.failures entries>. Retryable: <true|false>. Environment: <true|false>.
Suggested next action: <envelope.suggested_next_action>. Raw logs: <path or safe summary>.
What now? fix / retry / accept risk / abort.
```

**Phase 3 — Review:**
```
🔄 Phase 3: Review — invoking review then final whole-diff check against <base>.
🔄 Phase 3: Fast-path review — one combined review/final-check pass against <base>.
✓ Phase 3: review/fresh-eyes proof satisfied; <N> findings addressed.
⚡ Phase 3: combined review proof satisfied; no blockers.
```

**Phase 4 — Submit:**
```
🔄 Phase 4: Submit — paired-set check, fetch ticket, draft PR, push.
✓ Phase 4: PR opened at <url>.
```

If the run takes the existing-PR fast path, Phases 3 and 4 are replaced by:
```
🚀 Fast-path: pushing to existing PR `<url>` — review/PR-creation skipped.
```

Fast-path small-diff marker:
```
⚡ Fast-path: small diff eligible — preloading aux, batching safe gates, and using combined review.
```

## Probe-failure 3-way prompt — call-site phrasings

Every probe-failure prompt follows the three-clause failure shape from `output-templates.md`: name what's wrong → name what's still working → name what to do (the three options). Below are call-site-specific phrasings. The `<reason>` and `<value>` blanks come from the probe; the call-site narrator fills the "what's still working" clause.

**Phase 2b — quality-gate command probe:**
```
⚠️ The gate `<gate-name>` (`<scope.cwd>$ <command>`) failed to probe: <reason>.
<what's-working: e.g. "Gates 1 and 2 passed; this is gate 3 of 4 in the
frontend scope.">

What now?
  (a) load/fix the missing tool and retry
  (b) proceed without this gate this session (the rest of the gates still run)
  (c) abort
```

**Phase 2c — translation_sync.skill probe:**
```
⚠️ The translation-sync skill `<skill-name>` failed to probe: <reason>.
<what's-working: e.g. "All quality gates passed; translation paths were
touched, so this skill should run before PR handoff.">

What now?
  (a) install/load the skill and retry
  (b) proceed without translation sync this session (paths stay un-synced)
  (c) abort
```

**Phase 2d — browser_compat.skill probe:**
```
⚠️ The browser compatibility skill `<skill-name>` failed to probe: <reason>.
<what's-working: e.g. "All gates passed; browser compatibility is advisory and
doesn't block PR handoff.">

What now?
  (a) install/load the skill and retry
  (b) proceed without the advisory check this session
  (c) abort
```

**Phase 4a — ticket_source probe:**
```
⚠️ The ticket source `<type>:<value>` failed to probe: <reason>.
<what's-working: e.g. "All gates and review passed; we're at the PR handoff step
and need the ticket title for the PR.">

What now?
  (a) load the tool/command and retry
  (b) paste the title manually for this PR (workflow.md unchanged)
  (c) abort
```

(Note: ticket_source's `(b)` is paste-this-time, not skip-the-cap. The PR still gets created with a hand-typed title.)

**Phase 4b — pr_description.formatter_skill probe:**
```
⚠️ The PR description formatter `<skill-name>` failed to probe: <reason>.
<what's-working: e.g. "PR draft is composed; the formatter is the last step
before showing it for approval.">

What now?
  (a) load the skill and retry
  (b) use the unformatted draft this session
  (c) abort
```

**Phase 4 entry — paired-set front-load (domain_expert + knowledge_store):**

If both halves are configured, probe both. If both probes pass → no prompt; proceed silently. If either configured half fails to probe → single prompt covering the pair:
```
⚠️ Domain capture is misconfigured: <which half(s) failed and why>.
<what's-working: e.g. "All review gates passed; we're at the PR handoff step. The
PR can still go out without domain capture.">

What now?
  (a) load/fix and retry both probes
  (b) skip Phase 4d this session (PR opens without domain capture)
  (c) abort
```

If exactly one half is absent from config → no probe and no prompt; print one paired-half-missing inline note and treat 4d as unconfigured for this run. If neither half is configured → no probe and no prompt; print the domain-capture-disabled note at 4d.

## Capability-disabled inline notes

Printed inline at the relevant phase boundary when a capability is intentionally disabled or paired-half-missing. Single line, ≤120 chars, `💭` glyph for soft notes:

```
💭 Phase 2c skipped: translation sync not triggered for this diff.
💭 Phase 2c skipped: translation sync is disabled for this project.
💭 Phase 2d skipped: browser compatibility not triggered for this diff.
💭 Phase 2d skipped: browser compatibility is disabled for this project.
💭 Phase 2: clean evaluator not configured — using the working-tree gate path.
💭 Phase 4b: no PR description formatter configured — using the raw draft.
💭 Phase 4d skipped: domain capture not configured.
💭 Phase 4d skipped: paired-half-missing — only `domain_expert.agent` set; `knowledge_store.path` is absent.
💭 Phase 4d skipped: paired-half-missing — only `knowledge_store.path` set; `domain_expert.agent` is absent.
💭 Phase 4d skipped: work was purely mechanical (no new domain rules surfaced).
```

These notes are advisory, not failures. They never block the run and never trigger a prompt.

## Cache write warning

Printed at run end when the probe-cache write fails after an otherwise completed run:

```
⚠️ Couldn't write the probe cache to `<path>`: <error>. The run completed fine, but the next run will re-probe.
```

## PR creation success

Printed at Phase 4c after `gh pr create` succeeds (≤500 chars including surrounding context):

```
🚀 Opened PR <url>.

Title: `<title>`
Base:  `<base>`
Files: <N> changed, <K> additions, <M> deletions.

Proof: <required/advisory proof status summary>.

<optional inline notes from this run, e.g.:
- 💭 Phase 4d skipped: domain capture not configured.
- ⚠️ Translation files were AI-generated — flagged in the PR description for
  reviewer attention.>
```

Draft-bot-review variant adds:
```
🚀 Opened DRAFT PR <url>. Bot review pending; will mark ready after fixes.
```

## Verbose stamps — ready-for-review's per-phase layout

When `BEISLID_VERBOSE=1` is set, ready-for-review appends structured stamps under each phase summary and at run end. Layout follows the universal `---` divider rule from `output-templates.md`. Stamps augment the prose; they never replace it.

After each phase summary line:

```
✓ Phase 2: selected pre-pr proof satisfied in 38s; 0 staged/non-computational proof item(s) not applicable.
---
🎯 Phase 2 exit check: required pre-pr proof satisfied; <K> staged/non-computational proof item(s) not applicable; <N> autofixes applied.
✓ probe scopes.frontend.gates[0].command — cli:pnpm (probed <ISO-8601>)
✓ probe scopes.frontend.gates[1].command — cli:pnpm (cached, hash-matched)
— scopes.backend (not touched)
```

At run end, after the cache write-back:

```
🚀 Opened PR <url>.
---
🎯 Run exit check: <N> caps probed this run; <K> written back to cache; <M> session-skipped.
cache file:        <path>
cache valid until: <ISO-8601>
workflow_hash:     <hash>
repo_hash:         <hash>
host:              <detected>
```

Stamp-symbol legend (subset of the palette):

- `✓` — capability probed and resolved (or cached `ok` and within TTL).
- `✗` — capability probed and didn't resolve (failure surfaced via the 3-way prompt).
- `—` — capability not configured or not touched this run.
- `🎯` — phase or run exit check (verbose tier only).

Default mode (no `BEISLID_VERBOSE`) prints only the prose; never the stamps.

## Aux load stamps and loaded summary

Phase protocol files are normally loaded just in time; fast-path preloads Phase 2/3/4 after Phase 1. When `BEISLID_VERBOSE=1`, print one load stamp immediately after successfully reading a phase aux file:

```
✓ ready-for-review/phase-1-detect v1 loaded
✓ ready-for-review/phase-2-gates v1 loaded
✓ ready-for-review/phase-3-review v1 loaded
✓ ready-for-review/phase-4-submit v1 loaded
```

At run end, include a compact loaded/not-reached summary under the run exit check:

```
aux loaded:      phase-1-detect, phase-2-gates
aux not reached: phase-3-review, phase-4-submit
```

If an aux file cannot be read, hard-fail with:

```
🛑 Could not read `skills/ready-for-review/<phase-file>.md`. Ready-for-review cannot safely execute this phase from memory; reinstall Beislið or restore the file.
```

## Verbose transcript persistence

When `BEISLID_VERBOSE=1`, ready-for-review persists a best-effort local transcript at:

```
${BEISLID_STATE_DIR:-~/.local/state/beislid}/runs/ready-for-review/<repo_hash>/<timestamp>/transcript.md
```

The transcript is evidence, not hidden reasoning. Initialize it immediately after config/cache setup, before loading Phase 1, so early aux-load and phase-entry events are captured. Print user-facing orientation later, after Phase 1 knows branch/base/fast-path status. Append only at major boundaries:

- run start/config-cache setup
- aux file loaded
- phase entry
- phase exit
- state-changing probe decisions (new probe, failure, retry, proceed-this-session, abort)
- gate envelope summaries (gate name, stage, scope/cwd, command label, status, failures, retryable/environment flags, suggested action, raw-log reference, rich metadata used, autofix/user approval, skipped-by-stage when applicable)
- user approvals / hard gates (record the single approval prompt/decision without duplicating the question)
- external side effects (merge/rebase, commit, push, PR create, mark ready, cache write, memory capture)
- run end / abort

Do not log hidden reasoning, full raw stdout/stderr, env var values, auth headers/tokens, or secret-looking values. Redact secret-looking values as `[REDACTED]`. For command failures, log the envelope and raw-log path or transcript-safe summary, not full output.

Transcript persistence is best-effort in real runs. If writing fails, warn once and continue:

```
⚠️ Verbose transcript could not be written to `<path>`: <error>. Continuing without persisted transcript.
```

If a transcript was written, include one final soft note:

```
💭 Verbose transcript saved: `<path>`
```

Phase 5 smoke treats a missing or unwritten verbose transcript as a test failure, but normal ready-for-review runs do not block on transcript persistence.

Host-neutral transcript checkpoints:

```bash
run_dir="${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/runs/ready-for-review/${repo_hash}/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$run_dir"
transcript="$run_dir/transcript.md"
printf '# ready-for-review verbose transcript\n\nrepo: %s\nbranch: %s\nstarted: %s\n\n' "$PWD" "${branch:-unknown}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$transcript"
```

Append major events safely with short, redacted text only:

```bash
printf '\n## %s\n- %s\n' "<event title>" "<safe summary>" >> "$transcript"
```

If either command fails, emit the warning above once and set transcript status to unavailable. Before Phase 1 exits, transcript status must be either `initialized:<path>` or `unavailable:<reason>`.

## Hardening prompts

No ticket prompt:

```text
What is the ticket ID? Reply with an ID, or `none` for maintenance/no-ticket work. I will not infer one from open issues. If `none`, the PR title must not start with `none:`.
```

Default branch prompt:

```text
You are on `<base>` with local changes. Ready-for-review will not push or open a PR from the base branch. Choose a branch name and include set: all changes, selected paths, or abort. Untracked files are excluded unless explicitly named.
```

Stale-check failure prompt:

```text
I could not verify whether `<branch>` is current with `origin/<base>`. Retry fetch, proceed with freshness marked unknown, or abort?
```

Review timeout prompt:

```text
`<review-kind>` is still running after 5m. Continue waiting, cancel-and-salvage partial output, or abort ready-for-review?
```

Cancel-and-salvage summary:

```text
Review coverage is incomplete: `<review-kind>` was cancelled. Partial output: <usable findings or none>. Proceeding requires explicit reduced-coverage risk acceptance.
```

Workflow auth preflight warning:

```text
This PR changes GitHub workflow files, but `gh auth status` does not show `workflow` scope. Refresh auth, proceed with warning, or abort?
```

Scope expansion / keep-vs-split warning:

```text
This review/fix path is expanding into a new subsystem or second scope. Keep it in this PR, or split the new scope into a follow-up ticket?
```

Beislið skill-change warning:

```text
This branch changes Beislið skills/config. This session may not be dogfooding freshly edited skill files until restart/reinstall; I will treat those edits as potentially stale.
```

PR CI post-create note:

```text
PR created. Poll/report CI once before final handoff, then include the result in the summary.
```

Clean evaluator setup failure prompt:

```text
⚠️ The clean evaluator couldn't create or attach `<surface>`: <reason>.
<what's-working: e.g. "The branch, base, and candidate patch are known; only the clean surface is blocked.">

What now?
  (a) retry with a fresh clean surface
  (b) proceed without clean eval this session (if policy allows)
  (c) abort
```

PR create retry guidance:

```text
PR creation failed. I will retry from the repo root with `--head <branch>` and the already-approved title/body, or abort if you prefer.
```

Structured memory brief minimum shape. Run-end must append/print exactly one literal marker before final success text: `kind: ready-for-review-session-memory-v1` with the brief, or `memory brief unavailable:<reason>` if no save/print path exists. Prose like “brief summarized” is not enough:

```yaml
kind: ready-for-review-session-memory-v1
summary: "<short shipped-work summary>"
repo: "<repo path or slug>"
branch: "<branch>"
base: "<base>"
ticket: {id: "<id or none>", title: "<title or none>", url: "<url if known>"}
pr: {url: "<PR URL if created>", title: "<PR title>", base: "<base>"}
phase_path: "<new-pr | new-pr-fast-path | existing-pr-fast-path | aborted>"
evidence: {loaded_aux_files: ["<files>"], transcript: "<path or unavailable:reason>", gates: "<summary>", clean_eval: "<summary>", review: "<summary>"}
decisions: {accepted_risks: ["<risks>"], reduced_review_coverage: "<state>", domain_capture: "<state>"}
side_effects: ["<commit/push/PR/cache/memory events>"]
runtime: {host: "<detected>", timestamp: "<ISO-8601>", duration: "<duration if known>"}
```

## Char budgets (ready-for-review-specific)

- Orientation prose: ≤240 chars (one printed line at run start).
- Per-phase entry/exit one-liners: ≤120 chars each.
- Probe-failure prompts: ≤500 chars including the three-clause body.
- Capability-disabled inline notes: ≤120 chars each.
- PR creation success: ≤500 chars including surrounding context.

The general char-budget shape (orientation, action, failure) lives in `output-templates.md`. These numbers are ready-for-review's specific instances of it.
