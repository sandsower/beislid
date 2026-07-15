# Beislið Nopal seam protocol v1

This is the shared call contract for the deterministic decisions Beislið may delegate to the `nopal` binary: gate selection, action-policy verdicts, runtime placement, workflow normalization, and run-ledger writes.
Nopal is optional, and every delegated seam preserves a Beislið-native fallback.

## Probe: nopal_seam

`nopal_seam` is a `binary` probe configured by the optional `beislid:nopal_seam` workflow fence.
An absent block means `mode: prefer`, `binary: nopal`, and no minimum version.

- `mode: prefer` uses Nopal when the probe is valid and otherwise uses the relevant Beislið fallback without interrupting the user.
- `mode: require` blocks when the probe is missing, stale, malformed, incomplete, or below `min_version`.
- `mode: off` never probes or calls Nopal.

Set `nopal_bin` to the configured `binary` value, defaulting to `nopal`, and preserve it as one argv element rather than evaluating it as shell text.
Run `command -v -- "$nopal_bin"`, then `"$nopal_bin" info --json`.
Every delegated call below uses that same resolved executable.
The response must be a complete `nopal.info/v1` envelope with `ok: true`, a dotted-triple `version`, a nullable `commit`, and a string `capabilities[]` list.
Confirm `kind` before reading any other field.
Compare a configured minimum version component by component.
Detect a feature through membership in `capabilities[]`, never through help text or a version heuristic.

There is no retired-binary or `--version` compatibility probe.
Any malformed, incomplete, wrong-kind, or non-zero `nopal info --json` result makes the probe unavailable.
`prefer` then falls back and records the probe diagnostic, while `require` blocks with installation guidance.
Install a current archive from the `sandsower/nopal` GitHub Releases page, verify it against `SHA256SUMS`, place `nopal` on `PATH`, and rerun `nopal info --json`.

## Call contract

- Always pass `--json`.
- Parse the top-level `kind` field before reading response data.
- Match diagnostics by stable `code`, never by prose `message`.
- Invoke Nopal from the repository root unless a configured scope requires another `cwd`.
- Treat a missing required capability as probe unavailability, not as permission to guess another command shape.

### Exit-code semantics

For `gates`, `policy`, `validate`, `import`, and `ledger`, exit code follows the envelope's `ok` field.
Warnings do not make `ok` false, so callers must inspect `diagnostics[]` even after exit 0.
`policy_mode_unknown`, `policy_class_unknown`, and `stage_unknown` mean the input token was not normalized and the decision must not be trusted.

The informational `status`, `rondo`, and `run start` families can return exit 0 while their payload reports an unready state.
Those families are outside this seam, but callers that use them must read the payload's readiness field.

## Token normalization

Nopal uses snake_case while Beislið uses kebab-case for several workflow tokens.
Convert each token before calling Nopal.

| Beislið | Nopal |
|---|---|
| `supervised-auto` | `supervised_auto` |
| `unattended-auto` | `unattended_auto` |
| `workspace-write` | `workspace_write` |
| `dependency-install` | `dependency_install` |
| `network-read` | `network_read` |
| `git-local` | `git_local` |
| `git-remote` | `git_remote` |
| `secret-bearing` | `secret_bearing` |
| `read`, `destructive` | unchanged |
| `pre-pr` | `pre_pr` |
| `pre-commit` | `pre_commit` |

Other dashed gate stages use the same dash-to-underscore rule.

## The five delegated seams

### 1. Gate selection

```bash
"$nopal_bin" gates select --dir . --stage <snake_stage> [--changed-files <f1,f2,...>] --json
```

Require the `gates` capability.
The `nopal.gates.select/v1` response carries `selected[]` and `skipped[]`.
Run each `selected[].run.command` and preserve its selected gate identity for evidence reuse.
When Nopal is unavailable, use the selector-union algorithm in `workflow-md-format.md`.

### 2. Action-policy verdict and placement

```bash
"$nopal_bin" policy decide --dir . --mode <snake_mode> --action <stable-action-id> [--class <snake_class> ...] [--env <NAME> ...] --json
```

Require the `policy` capability.
The `nopal.policy_decision/v1` response carries `decision`, `placement`, `decision_source`, `placement_source`, `matched_rules[]`, and `explanation[]`.
Use `decide` so verdict and placement come from one call.
When Nopal is unavailable, use `beislid action-policy evaluate` as documented in `action-policy-protocol.md`.

### 3. Workflow normalization and `.nopal/` drift

```bash
"$nopal_bin" import beislid-workflow --dir . --source .beislid/workflow.md --output-dir .nopal --check --json
```

Require the `import` capability.
The `nopal.beislid_import/v1` response compares generated module semantics with committed JSONC, ignoring formatting-only differences.
A `beislid_import_drift` diagnostic means the committed modules must be regenerated and reviewed.

```bash
"$nopal_bin" import beislid-workflow --dir . --source .beislid/workflow.md --output-dir .nopal --write --overwrite --json
"$nopal_bin" validate --dir . --json
```

Regeneration is an explicit write and requires the normal approval for the active mode.
Validation reads `.nopal/nopal.jsonc` and the profile-required modules.
The manifest uses `version: nopal.project/v1`.

### 4. Run-ledger writes

```bash
"$nopal_bin" ledger init --dir . --skill <skill> [--flow <flow>] [--ticket-id ...] [--branch ...] --json
"$nopal_bin" ledger event --run-id <id> --type <event_type> [--json-file <path>] [--summary <text>] --json
"$nopal_bin" ledger checkpoint --run-id <id> --name <name> [--json-file <path>] [--resume-hint <text>] --json
"$nopal_bin" ledger gate --run-id <id> --name <name> --envelope-file <path> --json
"$nopal_bin" ledger interrupt --run-id <id> --reason <text> --json
"$nopal_bin" ledger finalize --run-id <id> --status <completed|interrupted|failed> [--report-file <path>] --json
"$nopal_bin" ledger resume [--flow <flow>] [--ticket-id ...] [--branch ...] --json
```

Require the `ledger` capability.
Nopal uses the same `run-ledger-v1` disk contract and `BEISLID_STATE_DIR` fallback as `beislid run-ledger`.
When Nopal is unavailable, call the matching `beislid run-ledger` command.
A `run_not_found` diagnostic from resume means there is no resumable run.

## Scratch-file convention

`--json-file` and `--envelope-file` require a real path.
Write structured payloads under the active run's artifact directory, or use a temporary file that is removed after the call.
Never interpolate payload content into the shell command.

## Fallback ladder

1. If `mode: off`, use the Beislið fallback immediately.
2. If the exact Nopal probe or a required capability is unavailable under `mode: prefer`, use the fallback and record a concise diagnostic.
3. If a valid Nopal call returns `ok: false` under `mode: prefer`, use the fallback for that call and preserve its diagnostic code.
4. If any required Nopal condition fails under `mode: require`, block instead of falling back.

## Evidence rule

Record Nopal envelopes as run-ledger artifacts rather than pasting full responses into chat or PR prose.
When no ledger is active, preserve the decision, placement, selected gate IDs, or drift result in the workflow's normal concise summary.

## Out of scope

- Beislið's export bundle formats remain owned by `beislid export validate`.
- Sandbox-baseline and uncommitted-change inputs remain Beislið evidence because `nopal policy decide --json` does not accept them.
- This cutover does not adopt additional Nopal capabilities such as review-risk or change Beislið's skill triggers, approvals, host adapters, or standalone fallbacks.
- Fields reported as `beislid_import_unsupported` remain authoritative in `.beislid/workflow.md` and stay on their existing Beislið path.
