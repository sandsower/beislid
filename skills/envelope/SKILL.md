---
name: envelope
description: Author, approve, and export execution envelopes for AFK slices in a standalone strong-model session. Use only when the user explicitly invokes /envelope with a ticket id, approved Work Contract/spec file, or batch. Other skills may recommend it but must never auto-route into it. Ends with an approved, validated, repo-committed bundle under .beislid/exports/ that an external runner executes later.
---

# Envelope

Turn approved planning context into exported execution envelopes: one `execution-envelope-v0` per AFK-ready slice, packaged as an `approved-slice-plan-export-v0` bundle that `rondo run-once --manifest <slice-manifest>` can execute in a fresh session with zero additional context.

**Trigger is explicit only.** The human chooses which model/session pays for authoring. When `kickoff` classifies work as multi_slice/AFK-suitable it may *recommend* running `/envelope` in a strong-model session; it never auto-routes here, and this skill never auto-routes back.

**Don't use this for:** interactive implementation (use `kickoff`), PR handoff (`ready-for-review`), or running exported work (that's rondo's job — Beislið owns envelope/export semantics; rondo owns execution and run evidence; no runtime service).

Project config: `<repo>/.beislid/workflow.md`. Probe lazily per `probe-semantics.md`; policy-check side effects per `action-policy-protocol.md`. Output copy lives in `envelope-templates.md`. AFK eligibility is judged against a versioned rubric, resolved repo-override-first: a `beislid:envelope` block in workflow.md may set `rubric_path` (a repo-relative `.md`, no `..`); otherwise the skill default `afk-rubric.md` applies.

## Read workflow.md

Read `<repo>/.beislid/workflow.md` and validate line 1 is exactly `<!-- beislid-workflow: v1 -->`; hard-fail and stop if missing or wrong (run `/setup` for fresh projects). Initialize the probe cache exactly as `kickoff` does (`repo_hash`, `workflow_hash`, `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/probes/<repo_hash>.json`, fresh/stale/cold). Print orientation prose from `envelope-templates.md` (≤240 chars).

For durable evidence, best-effort `beislid run-ledger init --skill envelope --flow envelope` with ticket/branch context when known. Warn on ledger failure; never block.

## Step protocol loading

Complete steps in order. At each step entry, read the step aux file and follow it as the authoritative protocol. If a step file cannot be read, hard-fail and stop:

> 🛑 Could not read `skills/envelope/<step-file>.md`. Envelope cannot safely execute this step from memory; reinstall Beislið or restore the file.

## Checklist and required outputs

1. **Intake** — read `step-1-intake.md`. Outputs: input kind, planning context (approved structure/Work Contract or planning-skill results), candidate slices, bundle-id.
2. **Author** — read `step-2-author.md`. Outputs: one draft `execution-envelope-v0` per AFK-candidate slice with autonomy lists, proof requirements, pause conditions, dependencies, expected delivery, self-contained prompt, repo pin.
3. **Approve** — read `step-3-approve.md`. Outputs: per-envelope verdicts (approve / reject / demote-to-HITL), approval metadata, or the zero-AFK terminal state.
4. **Export** — read `step-4-export.md`. Outputs: validated bundle path, `envelope_exported` checkpoint status, commit status, handoff guidance.

## Global tripwires

- **Fail-closed:** unapproved envelopes are never exported. Zero approved envelopes means no bundle, no checkpoint, no commit — print the verdict summary and recommend `kickoff` for HITL slices.
- **No implementation.** This skill plans, packages, and exports; it never starts the work it is packaging.
- **Manifest input means revision mode**, which ships in a later Beislið version. Detect it (a JSON file whose `kind`/`schema` matches export/manifest contracts) and stop with the revision-mode message from `envelope-templates.md`. Do not overwrite or re-author silently.
- **Existing bundle dir is a hard stop.** `.beislid/exports/<bundle-id>/` already existing means a prior export; overwriting would corrupt the future supersede chain. Stop with the collision message; the user must pick a new bundle-id or delete deliberately.
- **Validator is the gate.** `beislid export validate <bundle-dir>` must exit 0 before checkpoint or commit. Never hand-wave a failed validation.
- **Reuse planning skills** (`spec`, `break-spec`, `blueprint`) for thinking work; never reimplement their protocols here.
- Policy-check every side effect (workspace writes, checkpoint, `git.commit`); `ask` requires approval, `deny` stops with manual fallback.

## Run end

Write back probed capability entries to the probe cache as `kickoff` does (exclude `session_skip`, preserve doctor-owned fields). Finalize the run ledger with verdicts, bundle path, validator evidence, and commit status when active.

## Key principles

- One strong-model session produces a self-contained bundle; a cheaper session executes it later.
- Explicit human verdicts per envelope, in one sitting; rejects never block the batch.
- Everything after approval is mechanical: documented JSON conventions + a read-only validator.
