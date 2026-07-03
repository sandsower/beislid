# bei-131-normalizer-conformance

Source: BEI-131 (P1a fix-forward conformance spec), decisions record `docs/plans/2026-07-03-bei-131-canonical-parser-decisions.md`.
Approved 2026-07-03 by Vic Valenzuela; run_mode supervised-auto; provider codex; tier standard (prefer, research-v1 projection).

**Objective**: implement canonical parser decisions D1-D9b in `workflow_normalizer.py`, encode D1-D12 as a golden conformance corpus (`tests/conformance/cases/`) with runner (`scripts/run_conformance.py`), document the frozen error-code catalog (`docs/parser-conformance.md`), amend the canonical format doc, and add one CI job.

**Scope**: the normalizer, its tests, the new corpus/runner/catalog, `.beislid/workflow-md-format.md`, one job in `validate.yml`.
Excluded: `action_policy`/`validate_export` corpus (blocked on the P0 integrity bundle), release shipping (HITL).

**Autonomy**: local branch + commits only; deny remote writes, non-stdlib deps, and any deviation from decided semantics (conflicts pause).

**Proof**: unit tests (>=1 per decision) exit 0; corpus runner exits 0 (>=1 case per D1-D10 incl. doc-derived); `git diff --check` clean.

**Pause**: decision ambiguity/contradiction, unresolvable gate failure, scope drift toward the other trio scripts, CI permission needs.

**Delivery**: per-decision notes, catalog, corpus coverage map, doc amendments; human reviews corpus fidelity before PR. Release is a follow-up HITL slice.

Ownership: beislid defines semantics; rondo executes and keeps run evidence; memento captures learning; teotl is the umbrella.
