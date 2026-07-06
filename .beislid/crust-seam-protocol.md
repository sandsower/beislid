# Beislið crust seam protocol v1

Shared call contract for the five deterministic decisions Beislið skills delegate to the `crust` binary when it is present: gate selection, action-policy verdict, runtime placement, workflow normalization (`.crust/` drift), and run-ledger writes. Crust is optional in v1. Every seam below has a documented fallback to today's Python tool or prose rule, so a repo without `crust` on PATH behaves exactly as before.

This file is intentionally the single place that documents crust call shapes. Call sites in skill files point here rather than repeating the grammar.

## Probe: crust_seam

`crust_seam` is a `binary` probe (see `probe-semantics.md`). Configure it with the optional `beislid:crust_seam` workflow.md fence (see `workflow-md-format.md`); an absent block means `mode: prefer`, `binary: crust`, no `min_version` check.

- `mode: prefer` (default) — probe `crust`; on `ok` use the crust-first path below; on `missing`/stale, silently use the fallback path for that seam, no user-facing friction.
- `mode: require` — probe `crust`; on `missing`, hard-stop naming the install story (no published release yet: `cargo build --release -p crust-cli` from the crust repo, binary lands at `target/release/crust`). Never silently fall back when `require` is configured.
- `mode: off` — never probe or call crust; every seam uses its legacy path unconditionally.

Probe technique: `command -v crust`, then `crust --version`. Crust has no machine-readable version envelope in v1 — `--version` prints plain text `crust <major>.<minor>.<patch>` (observed: `crust 0.1.0`). Parse the trailing dotted triple and compare against configured `min_version` with a simple per-component integer compare; do not attempt full semver range parsing. A parse failure on `--version` output is `status: failed`, `probe_supported: true`.

## Call contract

- Always pass `--json`. Crust's default human output is TOON, not JSON; every documented call in this file and in consuming skills carries `--json`. The consistency checker greps for bare crust invocations missing it.
- Parse the top-level `kind` field (`crust.<name>/v1`) to confirm the response shape before reading other fields; treat an unexpected `kind` as a hard integration failure, not a seam miss.
- Match diagnostics by `code`, never by `message` text. `message` is prose and may change between crust releases; `code` is the stable contract (`policy_mode_unknown`, `policy_class_unknown`, `stage_unknown`, `manifest_missing`, `module_missing`, `run_not_found`, `beislid_import_unsupported`, etc.).
- `--dir` defaults to `.`; orchestrators invoke crust from the repo root unless a scope's `cwd` requires otherwise (same posture as gate `cwd` handling today).

### Exit-code semantics

For most subcommand families (`gates`, `policy`, `validate`, `import`, `ledger`), exit code tracks the payload's `ok` field: `ok: true` exits 0, `ok: false` exits 1. Diagnostics with `severity: warning` do not flip `ok` to `false`; only `severity: error` diagnostics correlate with a non-zero exit and `ok: false`.

**Payload-over-exit-code exceptions:** `crust status`, `crust rondo <cmd>`, and `crust run <cmd>` always exit 0, regardless of internal readiness. These are informational/coordination surfaces, not pass/fail checks. Read the payload's own readiness field instead of the exit code: `status` uses `ready`, `rondo health` uses `ok` inside the service object, `run start` uses `readiness_ready`. Never treat exit 0 from these three families as "green" without reading that field.

**`ok: true` does not always mean the verdict is trustworthy.** A call can return `ok: true` and exit 0 while a `severity: warning` diagnostic reports that an unnormalized token forced a fallback default rather than a real match. Always inspect `diagnostics[]` even on a green exit; codes `policy_mode_unknown`, `policy_class_unknown`, and `stage_unknown` mean the caller passed an unnormalized token — fix the token before trusting the decision, do not retry the same call and accept the fallback.

## Token normalization

Crust's vocabulary is snake_case throughout. Beislið's workflow.md and action-policy vocabulary is kebab-case in several places. Convert every kebab token to snake_case before calling crust; passing the kebab form does not error, it silently degrades to a built-in fallback default with a warning diagnostic (verified: `--mode supervised-auto` returns `ok: true` but matches no configured rule; `--mode supervised_auto` matches the repo's configured `allow` rule).

| beislid (kebab) | crust (snake_case) |
|---|---|
| `supervised-auto` | `supervised_auto` |
| `unattended-auto` | `unattended_auto` |
| `workspace-write` | `workspace_write` |
| `dependency-install` | `dependency_install` |
| `network-read` | `network_read` |
| `git-local` | `git_local` |
| `git-remote` | `git_remote` |
| `secret-bearing` | `secret_bearing` |
| `read`, `destructive` | unchanged (no dash) |
| `pre-pr` (gate stage) | `pre_pr` |
| `pre-commit` (gate stage) | `pre_commit` |

Other gate stages (`preflight`, `per-edit`, `post-pr`, `continuous`, `human-interrupt`) follow the same dash-to-underscore pattern; only `pre_pr` and `pre_commit` are exercised by this repo's own dogfood and were directly verified against the binary.

## The five delegated seams

### 1. Gate selection

```bash
crust gates select --dir . --stage <snake_stage> [--changed-files <f1,f2,...>] --json
```

`--changed-files` is comma-separated and/or repeated. Response `kind: crust.gates.select/v1` carries `selected[]` (each with `id`, `stage`, `run.command`, `via`) and `skipped[]` (each with `id`, `stage`, `reason`). Run `selected[].run.command` for every entry; `skipped[].reason` values include `stage_mismatch` and selector-driven skip reasons. This replaces the prose `gate_sets` selector-union algorithm in `workflow-md-format.md` when the seam is available; that algorithm remains the fallback and the doctor-visible source of truth for what crust is expected to compute.

### 2. Action-policy verdict and placement

```bash
crust policy decide --dir . --mode <snake_mode> --action <stable-action-id> [--class <snake_class> ...] [--env <NAME> ...] --json
```

Response `kind: crust.policy_decision/v1` carries `decision` (`allow`/`ask`/`deny`), `placement` (runtime isolation guidance, e.g. `shared_user_runtime`, `dedicated_repo_runtime`, `dedicated_run_runtime`, `blocked`), `decision_source`, `placement_source`, `matched_rules[]`, and `explanation[]`. This is the crust-first replacement for `beislid action-policy evaluate`; see `action-policy-protocol.md` for the full evaluator call contract and how the placement verdict is recorded and honored. `crust policy evaluate` (decision only) and `crust policy placement` (placement only) exist as narrower siblings; prefer `decide` so one call yields both fields.

Unknown/malformed mode or class does not error — crust falls back to conservative built-in defaults (observed: unknown class treated as protected/unsafe, deny-leaning) with a `policy_mode_unknown` / `policy_class_unknown` warning diagnostic. This is stricter than beislid's own unknown-action-asks default; never suppress the warning, it means a token needs normalizing.

### 3. Workflow normalization / `.crust/` drift

```bash
crust import beislid-workflow --dir . --source .beislid/workflow.md --output-dir .crust --json
```

Preview mode (no `--write`) is stateless and side-effect-free; diff its `outputs[].content` per module against the committed `.crust/*.jsonc` files to detect drift. Response `kind: crust.beislid_import/v1` carries `outputs[]` (module, path, action, bytes, content) and `diagnostics[]` naming every workflow.md field crust's v1 modules cannot represent yet (`beislid_import_unsupported`). A drifted repo re-runs with `--write --overwrite` after review.

```bash
crust validate --dir . --json
```

Validates `.crust/crust.jsonc` plus profile-required modules. `kind: crust.validation/v1`; `ok: false` with `code: manifest_missing` when `.crust/crust.jsonc` is absent — crust's importer does not generate the project manifest, it must be hand-authored once per repo (`version: crust.project/v1`, `project.name`, `profile`). Profile `portable` requires only `gates` + `policy` modules; `workflow` and `integrations` are accepted as additive extras.

### 4. Run-ledger writes

```bash
crust ledger init --dir . --skill <skill> [--flow <flow>] [--ticket-id ...] [--branch ...] --json
crust ledger event --run-id <id> --type <event_type> [--json-file <path>] [--summary <text>] --json
crust ledger checkpoint --run-id <id> --name <name> [--json-file <path>] [--resume-hint <text>] --json
crust ledger gate --run-id <id> --name <name> --envelope-file <path> --json
crust ledger interrupt --run-id <id> --reason <text> --json
crust ledger finalize --run-id <id> --status <completed|interrupted|failed> [--report-file <path>] --json
crust ledger resume [--flow <flow>] [--ticket-id ...] [--branch ...] --json
```

Same on-disk contract as `beislid run-ledger`: `crust ledger` reads `BEISLID_STATE_DIR` (or its own `--state-dir` override, which wins over the env var) and writes `${state_dir}/runs/<flow>/<repo_hash>/<run_id>/` with `run.json` (`kind: run-ledger-v1`), `events.jsonl`, and `transcript.md`. Verified byte-compatible field shape (`repo_hash`, `run_id`, `schema_version: 1`, `ticket`, `status`) against the same directory beislid's tool writes. `crust ledger resume` with no match returns `ok: false`, `code: run_not_found` — treat as "no resume available," not a hard error.

## Scratch-file convention

Crust has no stdin input for structured payloads. `--json-file` (ledger event/checkpoint) and `--envelope-file` (ledger gate) require a real file path. Write a scratch JSON file — under the active run-ledger artifact directory when a run is active, otherwise a `mktemp`-created temp file cleaned up after the call — then pass its path. Never pipe or shell-interpolate payload content.

## Fallback ladder (per seam)

1. `crust_seam` probe missing/stale, or `mode: off` — use the seam's legacy path immediately. No extra user-facing friction beyond doctor mentioning the miss.
2. `crust_seam` probe ok but a specific call returns `ok: false` with a real `severity: error` diagnostic — fall back to the legacy path for that call, and surface the crust diagnostic `code` (not the prose message) in the failure context.
3. `mode: require` and the probe is missing — hard-stop naming the install story; do not fall back.

Per-seam legacy paths: gate selection falls back to the `gate_sets`/`scopes`/top-level-`gates` selector algorithm in `workflow-md-format.md`; action-policy falls back to `beislid action-policy evaluate` per `action-policy-protocol.md`; workflow normalization falls back to doctor's own prose YAML validation of `workflow.md`; run-ledger falls back to `beislid run-ledger <cmd>`.

## Evidence rule

Record crust envelopes as run-ledger artifacts: write the JSON response to a scratch file under the active ledger's artifact directory and reference its path from the recording event/checkpoint, rather than pasting full envelopes into chat or ticket/PR prose. When no run ledger is active, a concise summary (decision/placement/selected-gate-ids) in the phase's normal output is enough.

## Out of scope (v1 carve-outs)

- **Risk classification, fast-path eligibility, and split-policy checks** (`ready-for-review` Phase 1) have no crust vocabulary yet and stay prose with this explicit carve-out. A follow-up crust ticket covers a review-risk/threshold policy surface.
- **Sandbox baseline** (`--sandbox-baseline`, `--uncommitted-changes` in `beislid action-policy evaluate`) has no crust `policy decide` v1 representation. Record it as evidence alongside the crust envelope; it no longer influences the crust verdict. `crust import beislid-workflow` diagnostics would flag sandbox-conditional rules if a repo had any (none observed in this repo's config).
- **Export bundle validation** (`beislid export validate <bundle-dir>` in `envelope`) has no crust equivalent. `crust export process` only builds/checks the normalized `crust.process_artifact/v1` provenance dump of `.crust/`, not beislid's `execution-envelope-v0` / `approved-slice-plan-export-v0` bundle contracts under `.beislid/exports/`. Envelope's export-validation seam stays on `beislid export validate` unconditionally.
- **`review_policy`, `ready_for_review`, `clean_eval`, and `babysit` workflow.md blocks** have no crust v1 module representation; `crust import beislid-workflow` reports each as `beislid_import_unsupported` and drops it from every `.crust/*.jsonc` draft. These stay fully on the Python/prose path in every mode.
