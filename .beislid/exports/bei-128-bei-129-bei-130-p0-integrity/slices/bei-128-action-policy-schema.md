# bei-128-action-policy-schema

Source: BEI-128 (teotl unification P0 batch, audit finding B12).
Approved: 2026-07-02T17:10:23Z by Vic Valenzuela (explicit per-envelope verdict).

**Objective:** action_policy payload keys validated against an explicit stdlib-only allowlist; unknown/missing required keys exit non-zero naming the key; decision defaults to deny (fail closed).

**Scope:** `scripts/action_policy.py` + `scripts/test_action_policy.sh`.

**Autonomy:** supervised-auto; local branch allowed; push/PR denied; non-stdlib deps denied.

**Proof:** `bash scripts/test_action_policy.sh` (with new fail-closed cases), `bash scripts/test_run_ledger.sh`, `git diff --check`.

**Pause on:** gate failure after retry, ambiguity, scope drift.

**Ordering:** runs before bei-129 (both edit action_policy.py); parallel with bei-130.
