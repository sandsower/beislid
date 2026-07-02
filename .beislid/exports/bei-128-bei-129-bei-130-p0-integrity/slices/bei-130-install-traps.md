# bei-130-install-traps

Source: BEI-130 (teotl unification P0 batch, audit finding B10).
Approved: 2026-07-02T17:10:23Z by Vic Valenzuela (explicit per-envelope verdict).

**Objective:** INT/TERM/ERR traps + staged atomic skill copies in `scripts/install_lib.sh` so an interrupted install never leaves an ownerless (forever user-owned) skill copy.

**Scope:** `scripts/install_lib.sh` + `scripts/test_install.sh`. Stays bash (spec decision 8).

**Autonomy:** supervised-auto; local branch allowed; push/PR denied; must test against a temp install target, never the real skills dir.

**Proof:** `bash scripts/test_install.sh` + kill-mid-copy repro with zero ownerless copies + `git diff --check`.

**Pause on:** gate failure after retry, ambiguity, scope drift.

**Ordering:** parallel with bei-128 (file-disjoint).
