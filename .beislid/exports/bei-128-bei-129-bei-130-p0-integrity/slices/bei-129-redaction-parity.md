# bei-129-redaction-parity

Source: BEI-129 (teotl unification P0 batch, audit finding B7).
Approved: 2026-07-02T17:10:23Z by Vic Valenzuela (explicit per-envelope verdict).

**Objective:** ledger redaction covers every action_policy secret pattern; a drift-failing test keeps them aligned.

**Scope:** `scripts/action_policy.py`, `scripts/run_ledger.py`, both test scripts.
Prefer the consistency-test approach over a shared module if sharing breaks single-file standalone execution.

**Autonomy:** supervised-auto; local branch allowed; push/PR denied; non-stdlib deps denied.

**Proof:** both tool test scripts green (incl. the new parity test) + `git diff --check`.

**Pause on:** gate failure after retry, ambiguity, scope drift.

**Ordering:** runs after bei-128 (both edit action_policy.py).
