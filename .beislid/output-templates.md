# Beislið output templates — shared primitives

Shape primitives every Beislið skill follows when narrating success or failure to the user. Loaded on demand from each consuming skill via a per-skill auxiliary symlink. Per-skill copy (audit narrations, prompt phrasings, char-budget numbers) lives alongside this file as `<skill>-templates.md` — see `doctor-templates.md` and `ready-for-review-templates.md`.

## Emoji palette (12)

Every skill draws from this fixed palette. No other glyphs in default-mode output.

| Glyph | Meaning |
|---|---|
| 📋 | Reading config / orientation |
| 🩺 | Doctor audit |
| 🔄 | Phase entry / re-probed / mid-progress |
| 💭 | Soft note / nudge / non-blocking advisory |
| ⚠️ | Warning — blocking or near-blocking |
| ✓ | Inline-only success marker |
| ✗ | Inline-only failure marker |
| 🛑 | Hard block — exit immediately |
| 🚀 | Shipped / external action complete |
| 📝 | Wrote a file |
| 🎯 | Phase exit check (verbose tier only) |
| 🔒 | Hard gate engaged |

`✓` and `✗` are inline-only — never as standalone status markers in default-mode prose. Hard-fail prose always leads with `🛑`. Soft notes inside otherwise-successful runs use `💭`. Capability probe failures lead with `⚠️` (the failure shape always offers a choice; it doesn't unilaterally exit).

## Three-clause failure shape

When narrating a failure that needs a user decision, every Beislið skill follows the same three-clause shape. At hard approval boundaries, the blocking approval question appears only once in the final user-facing response; progress/status prose may provide context or drafts, but never restate the question:

1. **Name what's wrong.** Specific to the failure — capability, value, reason.
2. **Name what's still working.** Acknowledges the rest of the configured surface that did resolve. Prevents the failure from feeling catastrophic when it isn't.
3. **Name what to do.** Either explicit options (a/b/c for probe-failure prompts) or actionable next steps (commands to run, files to edit).

```
⚠️ <clause 1: what's wrong>.
<clause 2: what's still working — acknowledges intact surface>.

What now? / Fix options:
  (a) <option 1>
  (b) <option 2>
  (c) <option 3>
```

Or for non-prompt failures (advisory):

```
⚠️ <clause 1>.
<clause 2>.

<clause 3: actionable next step in plain prose>.
```

If multiple capabilities fail at once, group them under a single three-clause block — don't repeat the shape per failure. The prose should read as one coherent narrative.

## Char-budget shape

Every skill picks specific numbers within this shape; the shape itself is uniform.

- **Orientation prose** (printed once per run, top of body): a single short paragraph that names what's about to happen and what context the skill loaded. Bounded — orchestrators pick ≤240 chars; doctor's success narration sits in the same band.
- **Action prose** (printed inside a phase or step): summarizes what just happened or is about to happen. Bounded by a small ceiling — typical numbers are ≤120 (per-phase one-liner), ≤500 (full audit success).
- **Failure prose** (printed when a failure surfaces): the three-clause shape above. Bounded slightly larger than action prose to fit the three clauses — typical numbers are ≤500 (probe-failure prompt) or ≤700 (full audit failure).

Per-skill template files instantiate these with concrete numbers.

## Gate result envelope

Gate-running orchestrators build a transcript-safe envelope for every configured gate run before prompting, handing context to review, or entering a fix loop. Raw stdout/stderr may be stored separately; prompts lead with the envelope.

```yaml
gate: {name: "<gate>", scope: "<scope or repo>", cwd: "<cwd>", command: "<label>"}
status: pass | fail | skipped | error
duration_ms: 0
summary: "one-line human/agent summary"
failures:
  - {type: "assertion|lint|collection|environment|timeout|unknown", location: "file/test if known", message: "short safe message"}
retryable: false
environment_failure: false
suggested_next_action: "fix code | install dependency | retry gate | inspect raw logs | accept risk"
raw_logs: {path: "<local path when captured>", transcript_safe_summary: "short excerpt or omitted"}
```

Parser rules:

- **Generic text parser:** exit 0 → `pass`; nonzero → `fail` unless the output points to command resolution, permissions, missing files, auth/network/cache/timeout, or tool startup, which becomes `error` with `environment_failure: true`. Extract the first actionable error lines, keep excerpts short, and mark transient/tooling failures `retryable: true`.
- **Pytest parser:** extract `FAILED`, `ERROR`, collection/import/setup failures, node IDs, file/line locations, and the short test summary. Assertion failures are normally `retryable: false`; collection/import/tool startup problems that indicate missing environment or dependencies set `environment_failure: true` and suggest environment repair before code changes.

Failure prompts must show `summary`, key `failures`, `retryable`, `environment_failure`, `suggested_next_action`, and raw-log path/summary. Do not dump full raw logs into the prompt unless the user asks.

## Model routing status envelope

When a host/orchestrator evaluates `beislid:model_routing`, summarize the result before invoking the routed skill or subagent:

```yaml
model_routing: {skill: "<skill>", status: honored | fallback | unsupported | blocked, requested: ["opus"], resolved: "<model or host-default>", mode: prefer | require, reason: "short explanation"}
```

`prefer` routes may continue with `fallback` or `unsupported`; `require` routes use `blocked` when no candidate can be honored and must stop before the routed invocation. Do not claim routing was honored unless the host actually selected one of the requested candidates.

## Verbose-stamps layout

When `BEISLID_VERBOSE=1` is set, structured stamps appear *under* the prose, separated by a `---` divider. Stamps never replace the prose narration — they augment it.

```
<prose narration as in default mode>

---

<structured stamps — one line per item, no fixed-width columns>
```

Stamps should be reference material readable line by line, not a CI-style table. Each consuming skill defines what stamps it emits; the divider rule and "augment, don't replace" invariant are universal.

Stamp glyphs (subset of the palette):

- `✓` — item resolved / passed.
- `✗` — item failed / didn't resolve.
- `—` — item disabled or not configured (no probe was run).

## Inline-note placement

Inline `⚠️` and `💭` notes belong inside the surrounding prose where they make sense — directly after the sentence they qualify, never as a separate bullet list outside the prose.

- A capability whose probe surfaces a parse warning gets the `⚠️` note inline after the configured-summary sentence that mentions that capability.
- An unknown / unrecognized config key gets a `💭` note inline at the end of the configured-summary sentence.
- A capability that's intentionally disabled at the project level gets a `💭` note when the skipped phase boundary is announced.

Notes are short — one emoji + a phrase, never sentences. Per-skill templates define the exact phrasings.
