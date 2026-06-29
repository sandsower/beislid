# Beislið doctor — output templates

Doctor-specific copy: audit narration templates, cache file schema, doctor's verbose stamps. Loaded on demand from `skills/doctor/SKILL.md` via the per-skill auxiliary symlink. Shared primitives (12-emoji palette, three-clause shape, char-budget shape, verbose-stamps layout description, inline-note placement) live in `output-templates.md` alongside this file; doctor symlinks both.

## Audit narration — success template

When every probe resolves cleanly, doctor narrates in this shape (≤500 chars):

```
🩺 **Workflow check on `<project_name>`.**

Configured: <one or two sentences listing what's set up — issue tracker, scopes/setup, which optional skills are wired>. <Translation sync / browser compat / domain capture, etc.> are off in this project.

Just probed all of them — ✓ everything resolves. Cache refreshed, valid for the
next <ttl_hours>h.
```

The "Configured:" sentence summarizes what's present. The "off in this project" sentence summarizes what's intentionally disabled. The probe result + cache validity is the closer. When gates are configured, mention whether they are legacy flat, staged rich, or mixed; do not warn merely because a gate is flat.

## Audit narration — failure template (three-clause shape)

When any probe fails, doctor follows the three-clause failure shape from `output-templates.md` (≤700 chars): name what's wrong → name what's still working → name what to do.

```
🩺 **Workflow check on `<project_name>`.**

⚠️ <name what's wrong, e.g. "The Linear MCP tool didn't resolve — workflow.md
points at `mcp__plugin_linear_linear__get_issue` but it isn't registered in
this session. Probably a plugin rename.">

✓ <name what's still working — list capabilities that resolved cleanly, e.g.
"The other 6 capabilities resolve fine.">

**Fix options:**
- <option 1, e.g. "reload the Linear plugin">
- <option 2, e.g. "update workflow.md to the new tool name">

<optional disabled-state context, e.g. "Translation sync is intentionally off
in this project, so that's not a problem.">
```

If multiple capabilities fail, the `⚠️` clause names them grouped by symptom (e.g. "Two MCP tools didn't resolve…") and the fix options cover the group. Don't write a separate three-clause block per failure — keep the audit a single coherent narrative.

## Audit inline notes

Inline `⚠️` and `💭` notes belong inside the audit narration, where they make sense:

- After the corresponding capability sentence for `⚠️` parse-failure or duplicate-key warnings
- At the end of the configured-summary sentence for `💭` unknown-key notes
- For gates: flat `name` + `command` gates are ok; staged rich gates are ok; warn only for invalid stage/execution values, missing executable `command` on a P0 command gate, or unsafe metadata such as `parallel_safe: true` with `mutates: true`
- For PR reviews: `pr_review_source` without `pr_review_update` is read-only and ok; `pr_review_update` without `pr_review_source` is a warning; `pr_review_update.type: manual` is manual-by-design and ok; `pr_review_source.type: paste` is manual-by-design and ok
- Never as a separate bullet list outside the prose

(General inline-note placement rules — single emoji + short phrase, never sentences — live in `output-templates.md`.)

## Cache file schema

The probe cache JSON written to `<state_dir>/probes/<repo_hash>.json`:

```json
{
  "schema": 1,
  "doctor_run_at": "2026-04-29T15:30:00Z",
  "workflow_hash": "a1b2c3d4e5f6...",
  "repo_hash": "abc1234def56",
  "host": "claude",
  "project_name": "taumar",
  "cache_ttl_hours": 24,
  "capabilities": {
    "ticket_source": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "cli",
      "value": "gh"
    },
    "domain_expert.agent": {
      "status": "failed",
      "probe_supported": false,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "subagent",
      "value": "researcher",
      "reason": "host (codex) has no subagent mechanism"
    },
    "translation_sync.skill": {
      "status": "disabled"
    },
    "pr_review_source": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "cli",
      "value": "gh"
    },
    "pr_review_update": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "manual",
      "value": "(manual at runtime)"
    },
    "lifecycle_actions.break_spec_approved": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "artifact",
      "value": "(prompted artifact at runtime; failure: prompt)"
    },
    "lifecycle_actions.spec_approved": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "mixed",
      "value": "artifact + tracker + cli: planning-hook"
    },
    "lifecycle_actions.blueprint_approved": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "mixed",
      "value": "artifact + cli: planning-hook"
    },
    "lifecycle_actions.kickoff_context_ready": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "artifact",
      "value": "(prompted artifact at runtime; failure: prompt)"
    },
    "lifecycle_actions.implementation_plan_created": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "artifact",
      "value": "(auto artifact at runtime; failure: continue)"
    },
    "lifecycle_actions.review_feedback_loaded": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "artifact",
      "value": "(reserved checkpoint artifact; not executed by P0 skills)"
    },
    "lifecycle_hooks": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "validation",
      "value": "phases: spec, blueprint, implement, verify, review, fresh_eyes, ready_for_review, review_response; trigger types: paths, exclude, scopes, branch_pattern"
    },
    "action_policy": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "validation",
      "value": "modes: supervised-auto, unattended-auto; unattended sandbox: non-default-branch; known actions: 11"
    },
    "clean_eval": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "validation",
      "value": "mode: require; surface: auto; artifact_root: .beislid/clean-eval"
    },
    "ship_time_artifacts": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "validation",
      "value": "mode: remind; planning-artifact summary only"
    },
    "model_routing": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "validation",
      "value": "default: sonnet/prefer; overrides: 2; required routes: 1"
    },
    "visual_surfaces": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "validation",
      "value": "provider: lavish-axi; mode: prompt; artifact_root: .lavish; artifact_retention: local; workflow overrides: 2; plugin: enabled"
    },
    "workflow_signals": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "validation",
      "value": "mode: auto; sinks: tmux-glance; skill overrides: 2; tmux-glance: present"
    },
    "babysit": {
      "status": "ok",
      "probe_supported": true,
      "probed_at": "2026-04-29T15:30:00Z",
      "probe_kind": "validation",
      "value": "goal: 50k; review-response loop: on; gates before push: on; merge/memento/retro: ask/ask/ask"
    }
  }
}
```

Field rules:

- `schema` — always `1` for v0.2; mismatched schema in a read invalidates the entire cache (doctor reprobes and rewrites at the version it knows).
- `host` — best-effort detection (`claude`, `codex`, `pi`, or `unknown`). Stamped at write time.
- `project_name` — basename of `git rev-parse --show-toplevel`.
- `cache_ttl_hours` — read from `beislid:probe_cache.ttl_hours` in workflow.md; defaults to `24`.
- `probe_supported` — `false` only when the host literally cannot probe the kind (e.g., subagent probe on a host without subagents). Capability-not-found-in-session uses `probe_supported: true` with `status: missing`.
- `value` — what was probed or validated (tool name, command binary, path, artifact runtime policy, action-policy summary, etc.). Omitted on `disabled` entries. For reserved checkpoint artifact events, records a validation message such as `(reserved checkpoint artifact; not executed by P0 skills)` when their shape is valid but no P0 skill executes them. For `action_policy`, summarize effective modes, sandbox minimums, action overrides, fallback decisions when configured, and known-action registry size; do not store the whole policy table in the cache.
- `reason` — only on `missing` and `failed`. Always omitted on `ok` and `disabled`.
- `probed_at`, `probe_kind`, `value` — omitted on `disabled` entries (no probe was run).

Orchestrators (ready-for-review, kickoff, review-response) write back individual capability entries when they probe lazily. They do NOT write `(b)`-skipped entries — those are session-only by contract; the next run re-prompts. They do NOT update top-level fields except `workflow_hash` and `cache_ttl_hours` (read from workflow.md). Doctor remains the only writer of `doctor_run_at`.

## Verbose stamps — doctor's per-capability layout

When `BEISLID_VERBOSE=1` is set, doctor appends a `---` separator and structured stamps under the prose narration. Layout (the `---` divider rule comes from `output-templates.md`):

```
🩺 **Workflow check on `<project_name>`.** <prose narration>

---

✓ ticket_source     cli:gh                                  ok (probed <ISO-8601>)
✗ domain_expert.agent  subagent:researcher                 missing (host has no subagents)
✓ gates              mixed legacy/rich staged gates ok (pre-pr executable)
— scopes             not configured
— translation_sync   disabled
— browser_compat     disabled
— knowledge_store    not configured
✓ pr_review_source cli:gh                                  ok (probed <ISO-8601>)
✓ pr_review_update manual                                  ok (manual at runtime)
✓ lifecycle_actions.break_spec_approved artifact            ok (prompted artifact at runtime)
✓ lifecycle_actions.spec_approved mixed                    ok (artifact + tracker + cli: planning-hook)
✓ lifecycle_actions.blueprint_approved mixed               ok (artifact + cli: planning-hook)
✓ lifecycle_actions.kickoff_context_ready artifact          ok (prompted artifact at runtime)
✓ lifecycle_actions.implementation_plan_created artifact    ok (auto artifact at runtime)
✓ lifecycle_actions.review_feedback_loaded artifact         ok (reserved; not executed by P0 skills)
✓ lifecycle_hooks validation                                ok (phases: spec..review_response; trigger types: paths/scopes/branch_pattern)
✓ action_policy validation                                  ok (unattended sandbox: non-default-branch; known actions: 11)
✓ clean_eval validation                                     ok (mode: require; surface: auto; artifact_root: .beislid/clean-eval)
✓ ship_time_artifacts validation                            ok (mode: remind; planning-artifact summary only)
✓ workflow_signals validation                               ok (sinks: tmux-glance; skill overrides: 2)
✓ babysit validation                                        ok (goal: 50k; closeout: ask/ask/ask)
cache file:        <path>
cache valid until: <ISO-8601>
workflow_hash:     <hash>
repo_hash:         <hash>
host:              <detected>
```

Stamp legend:

- `✓` — `status: ok`. Capability probed and resolved.
- `✗` — `status: missing` or `failed`. Capability probed and didn't resolve.
- `—` — `status: disabled` or capability not configured at all. No probe was run.

One line per capability. Capabilities are listed in the order they appear in workflow.md, followed by metadata lines (cache file path, validity, hashes, host) at the end. No fixed-width column padding required — the stamp output is reference material, not a CI-style table.

## Char budgets (doctor-specific)

- Audit success narration: ≤500 chars.
- Audit failure narration: ≤700 chars.
- Inline notes inside narration: ≤80 chars per note.

The general char-budget shape (orientation prose, action prose, failure prose) lives in `output-templates.md`. These numbers are doctor's specific instances of it.
