# bei-127-run-ledger-locking

Source: BEI-127 (teotl unification P0 batch, audit findings B3 + B11).
Approved: 2026-07-04T16:22:17Z by Vic Valenzuela (explicit per-envelope verdict).

**Objective:** run.json read-modify-write and `next_attempt_dir` serialized under a cross-process `fcntl.flock` lock so the demonstrated lost-update repro passes (20 concurrent event appends → `events.count == 20 ==` jsonl line count); explicit `--run-id` collision errors loudly instead of silently creating `<id>-2`.

**Design (pre-decided):** blocking `LOCK_EX` on a dedicated never-replaced `<run_dir>/.lock` (not run.json - `os.replace` would detach the flock), via a `run_lock(run_dir)` context manager.
Critical sections: entire `append_event` body, `record_checkpoint` RMW, and `next_attempt_dir` (gains a `run_dir` parameter from its single caller).
`command_init`: explicit `--run-id` + existing dir → diagnostic + non-zero exit; auto ids keep the suffix loop with `mkdir(exist_ok=False)` as arbiter.
Repro encoded as a failing test first.

**Scope:** `scripts/run_ledger.py` + `scripts/test_run_ledger.sh` + new `scripts/test_run_ledger_concurrency.py`.
Excluded: ledger schema, ghost `"active"` status (B14), redaction (BEI-129, landed), parser (BEI-131, landed).

**Autonomy:** supervised-auto; local branch allowed; push/PR denied; non-stdlib deps denied; real state-dir writes in tests denied (temp isolation required).

**Proof:** `python3 scripts/test_run_ledger_concurrency.py` (new), `bash scripts/test_run_ledger.sh`, cross-breakage `test_action_policy.sh` + `test_workflow_normalizer.py` + `test_validate_export.sh`, `git diff --check`.

**Pause on:** proof failure after one repair attempt, acceptance ambiguity, scope drift, pre-existing red at base, `fcntl` unavailable.

**Tier:** heavy (prefer); gate_repair standard. Provider: codex.

**Delivery:** locking design as implemented + failing-first repro evidence; changed_files + proof_results; next step is human strong review (concurrency), then ready-for-review handoff.
