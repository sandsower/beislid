#!/usr/bin/env bash
# Tests for scripts/process_export.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
EXPORTER="$REPO_DIR/scripts/process_export.py"
CLI="$REPO_DIR/bin/beislid"

pass=0
fail=0
failures=()
TMP=""

setup_fixture() {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/repo/.beislid"
  cat >"$TMP/repo/.beislid/workflow.md" <<'EOF'
<!-- beislid-workflow: v1 -->

# Test workflow

## Quality gates

```beislid:gates
- name: validate-skills
  command: 'python3 scripts/validate_skills.py'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: install-tests
  command: 'bash scripts/test_install.sh'
  timeout_seconds: 600
  cost: moderate
```
EOF
  cat >"$TMP/repo/.beislid/action-policy.json" <<'EOF'
{
  "modes": {
    "supervised-auto": {
      "actions": {
        "ticket.fetch": "allow"
      }
    }
  }
}
EOF
}

teardown() {
  [[ -n "${TMP:-}" ]] && rm -rf "$TMP"
}

note_fail() {
  echo "    $1" >&2
}

run_test() {
  local name="$1" fn="$2"
  echo "-- $name"
  setup_fixture
  if "$fn"; then
    pass=$((pass + 1))
    echo "   pass"
  else
    fail=$((fail + 1))
    failures+=("$name")
    echo "   FAIL" >&2
  fi
  teardown
}

json_get() {
  python3 - <<'PY' "$1" "$2"
import json, sys
payload = json.loads(sys.argv[1])
cur = payload
for part in sys.argv[2].split('.'):
    if isinstance(cur, list):
        cur = cur[int(part)]
    else:
        cur = cur[part]
print(cur)
PY
}

artifact_path() {
  echo "$TMP/repo/.beislid/exports/process.json"
}

run_export() {
  python3 "$EXPORTER" export --repo "$TMP/repo" "$@"
}

test_happy_path_export() {
  run_export >"$TMP/out.txt" 2>&1 || { note_fail "export failed: $(cat "$TMP/out.txt")"; return 1; }
  [[ -f "$(artifact_path)" ]] || { note_fail "artifact not written"; return 1; }
  local payload
  payload="$(cat "$(artifact_path)")"
  [[ "$(json_get "$payload" schema)" == "beislid-process-artifact-v1" ]] || { note_fail "wrong schema"; return 1; }
  [[ "$(json_get "$payload" status)" == "approved" ]] || { note_fail "wrong status"; return 1; }
  [[ -n "$(json_get "$payload" id)" ]] || { note_fail "missing id"; return 1; }
  [[ "$(json_get "$payload" gates.0.name)" == "validate-skills" ]] || { note_fail "gate 0 name"; return 1; }
  [[ "$(json_get "$payload" gates.0.command)" == "python3 scripts/validate_skills.py" ]] || { note_fail "gate 0 command"; return 1; }
  [[ "$(json_get "$payload" action_policy.decision)" == "ask" ]] || { note_fail "policy fixture decision"; return 1; }
  [[ "$(json_get "$payload" action_policy.policy_file)" == ".beislid/action-policy.json" ]] || { note_fail "policy_file pointer"; return 1; }
  [[ "$(json_get "$payload" metadata.policy_source)" == "action-policy.json" ]] || { note_fail "policy_source"; return 1; }
  local wf_hash
  wf_hash="$(git hash-object "$TMP/repo/.beislid/workflow.md")"
  [[ "$(json_get "$payload" metadata.source_hashes.workflow.hash)" == "$wf_hash" ]] || { note_fail "workflow hash mismatch"; return 1; }
  [[ "$(json_get "$payload" metadata.source_hashes.workflow.path)" == ".beislid/workflow.md" ]] || { note_fail "workflow hash path"; return 1; }
}

test_cli_dispatch() {
  local out
  out="$(BEISLID_HOME="$REPO_DIR" "$CLI" process export --repo "$TMP/repo")" || { note_fail "CLI dispatch failed"; return 1; }
  grep -qF "wrote .beislid/exports/process.json" <<<"$out" || { note_fail "unexpected CLI output: $out"; return 1; }
  BEISLID_HOME="$REPO_DIR" "$CLI" process check --repo "$TMP/repo" >/dev/null || { note_fail "CLI check failed on fresh artifact"; return 1; }
}

test_timeout_seconds_converts_to_ms() {
  run_export >/dev/null 2>&1 || { note_fail "export failed"; return 1; }
  local payload
  payload="$(cat "$(artifact_path)")"
  [[ "$(json_get "$payload" gates.1.timeout_ms)" == "600000" ]] || { note_fail "timeout_ms not converted"; return 1; }
}

test_non_contract_gate_fields_dropped() {
  run_export >/dev/null 2>&1 || { note_fail "export failed"; return 1; }
  local payload
  payload="$(cat "$(artifact_path)")"
  ! grep -qF '"parallel_safe"' <<<"$payload" || { note_fail "parallel_safe leaked into artifact"; return 1; }
  ! grep -qF '"cost"' <<<"$payload" || { note_fail "cost leaked into artifact"; return 1; }
  ! grep -qF '"mutates"' <<<"$payload" || { note_fail "mutates leaked into artifact"; return 1; }
}

test_gate_passthrough_fields() {
  cat >"$TMP/repo/.beislid/workflow.md" <<'EOF'
<!-- beislid-workflow: v1 -->

```beislid:gates
- name: autofix
  command: 'make fix'
  action_id: gate.autofix
  action_classes:
    - workspace-write
  reason: 'declared by test'
```
EOF
  run_export >/dev/null 2>&1 || { note_fail "export failed"; return 1; }
  local payload
  payload="$(cat "$(artifact_path)")"
  [[ "$(json_get "$payload" gates.0.action_id)" == "gate.autofix" ]] || { note_fail "action_id dropped"; return 1; }
  [[ "$(json_get "$payload" gates.0.action_classes.0)" == "workspace-write" ]] || { note_fail "action_classes dropped"; return 1; }
  [[ "$(json_get "$payload" gates.0.reason)" == "declared by test" ]] || { note_fail "reason dropped"; return 1; }
}

test_gate_missing_command_fails() {
  cat >"$TMP/repo/.beislid/workflow.md" <<'EOF'
<!-- beislid-workflow: v1 -->

```beislid:gates
- name: broken-gate
  cost: cheap
```
EOF
  if run_export >"$TMP/out.txt" 2>&1; then
    note_fail "expected export to fail on gate without command"
    return 1
  fi
  grep -qF "missing a non-empty command" "$TMP/out.txt" || { note_fail "unexpected error: $(cat "$TMP/out.txt")"; return 1; }
}

test_inline_policy_fallback() {
  rm "$TMP/repo/.beislid/action-policy.json"
  cat >>"$TMP/repo/.beislid/workflow.md" <<'EOF'

```beislid:action_policy
modes:
  supervised-auto:
    actions:
      # read-only fetch is fine
      ticket.fetch: allow
```
EOF
  run_export >"$TMP/out.txt" 2>&1 || { note_fail "export failed: $(cat "$TMP/out.txt")"; return 1; }
  grep -qF "inline beislid:action_policy block" "$TMP/out.txt" || { note_fail "missing materialization guidance"; return 1; }
  local payload
  payload="$(cat "$(artifact_path)")"
  [[ "$(json_get "$payload" metadata.policy_source)" == "inline-block" ]] || { note_fail "policy_source"; return 1; }
  [[ "$(json_get "$payload" action_policy.decision)" == "ask" ]] || { note_fail "fixture decision"; return 1; }
  grep -qF '"ticket.fetch": "allow"' "$(artifact_path)" || { note_fail "inline policy content missing"; return 1; }
}

test_no_policy_warns_and_exports_empty() {
  rm "$TMP/repo/.beislid/action-policy.json"
  run_export >"$TMP/out.txt" 2>&1 || { note_fail "export failed"; return 1; }
  grep -qF "warning: no action policy found" "$TMP/out.txt" || { note_fail "missing no-policy warning"; return 1; }
  local payload
  payload="$(cat "$(artifact_path)")"
  [[ "$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['action_policy'])" "$payload")" == "{}" ]] || { note_fail "expected empty action_policy"; return 1; }
}

test_check_fresh_ok() {
  run_export >/dev/null 2>&1
  python3 "$EXPORTER" check --repo "$TMP/repo" >"$TMP/out.txt" 2>&1 || { note_fail "check failed on fresh artifact: $(cat "$TMP/out.txt")"; return 1; }
  grep -qF "ok:" "$TMP/out.txt" || { note_fail "missing ok line"; return 1; }
}

test_check_stale_after_gate_edit() {
  run_export >/dev/null 2>&1
  printf '\n<!-- edited -->\n' >>"$TMP/repo/.beislid/workflow.md"
  if python3 "$EXPORTER" check --repo "$TMP/repo" >"$TMP/out.txt" 2>&1; then
    note_fail "expected check to fail after workflow edit"
    return 1
  fi
  grep -qF "STALE" "$TMP/out.txt" || { note_fail "missing STALE marker"; return 1; }
  grep -qF "beislid process export" "$TMP/out.txt" || { note_fail "missing remediation"; return 1; }
}

test_check_hand_edited_artifact_fails() {
  run_export >/dev/null 2>&1
  python3 - "$(artifact_path)" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    artifact = json.load(f)
artifact["gates"][0]["command"] = "echo hacked"
with open(path, "w") as f:
    json.dump(artifact, f, indent=2, sort_keys=True)
    f.write("\n")
PY
  if python3 "$EXPORTER" check --repo "$TMP/repo" >"$TMP/out.txt" 2>&1; then
    note_fail "expected check to fail on hand-edited artifact"
    return 1
  fi
  grep -qF "hand-edited" "$TMP/out.txt" || { note_fail "missing hand-edit diagnosis: $(cat "$TMP/out.txt")"; return 1; }
}

test_check_missing_artifact_fails() {
  if python3 "$EXPORTER" check --repo "$TMP/repo" >"$TMP/out.txt" 2>&1; then
    note_fail "expected check to fail when artifact missing"
    return 1
  fi
  grep -qF "missing" "$TMP/out.txt" || { note_fail "missing missing-artifact diagnosis"; return 1; }
}

test_reexport_is_byte_stable() {
  run_export >/dev/null 2>&1
  local first
  first="$(shasum -a 256 "$(artifact_path)")"
  run_export >/dev/null 2>&1
  [[ "$(shasum -a 256 "$(artifact_path)")" == "$first" ]] || { note_fail "re-export changed bytes"; return 1; }
}

test_malformed_yaml_hard_fails() {
  cat >"$TMP/repo/.beislid/workflow.md" <<'EOF'
<!-- beislid-workflow: v1 -->

```beislid:gates
- name: bad
  command: |
    multi
    line
```
EOF
  if run_export >"$TMP/out.txt" 2>&1; then
    note_fail "expected export to fail on multiline scalar"
    return 1
  fi
  grep -qF "unsupported YAML construct" "$TMP/out.txt" || { note_fail "unexpected error: $(cat "$TMP/out.txt")"; return 1; }
}

test_yaml_anchor_hard_fails() {
  cat >"$TMP/repo/.beislid/workflow.md" <<'EOF'
<!-- beislid-workflow: v1 -->

```beislid:gates
- name: bad
  command: &anchor 'echo hi'
```
EOF
  if run_export >"$TMP/out.txt" 2>&1; then
    note_fail "expected export to fail on YAML anchor"
    return 1
  fi
  grep -qF "unsupported YAML construct" "$TMP/out.txt" || { note_fail "unexpected error: $(cat "$TMP/out.txt")"; return 1; }
}

test_wrong_header_hard_fails() {
  sed -i '' '1s/.*/<!-- beislid-workflow: v2 -->/' "$TMP/repo/.beislid/workflow.md"
  if run_export >"$TMP/out.txt" 2>&1; then
    note_fail "expected export to fail on wrong header"
    return 1
  fi
  grep -qF "line 1 must be exactly" "$TMP/out.txt" || { note_fail "unexpected error: $(cat "$TMP/out.txt")"; return 1; }
}

run_test "happy path export" test_happy_path_export
run_test "CLI dispatch" test_cli_dispatch
run_test "timeout_seconds converts to timeout_ms" test_timeout_seconds_converts_to_ms
run_test "non-contract gate fields dropped" test_non_contract_gate_fields_dropped
run_test "gate passthrough fields kept" test_gate_passthrough_fields
run_test "gate missing command fails" test_gate_missing_command_fails
run_test "inline policy fallback with guidance" test_inline_policy_fallback
run_test "no policy warns and exports empty" test_no_policy_warns_and_exports_empty
run_test "check fresh ok" test_check_fresh_ok
run_test "check stale after gate edit" test_check_stale_after_gate_edit
run_test "check hand-edited artifact fails" test_check_hand_edited_artifact_fails
run_test "check missing artifact fails" test_check_missing_artifact_fails
run_test "re-export is byte-stable" test_reexport_is_byte_stable
run_test "malformed YAML hard-fails" test_malformed_yaml_hard_fails
run_test "YAML anchor hard-fails" test_yaml_anchor_hard_fails
run_test "wrong workflow header hard-fails" test_wrong_header_hard_fails

test_id_is_checkout_independent() {
  (cd "$TMP/repo" && git init -q && git remote add origin git@github.com:example/myproject.git)
  run_export >/dev/null 2>&1 || { note_fail "export failed"; return 1; }
  local payload
  payload="$(cat "$(artifact_path)")"
  [[ "$(json_get "$payload" id)" == "beislid:myproject" ]] || { note_fail "id not derived from origin: $(json_get "$payload" id)"; return 1; }
}

run_test "id derives from origin not directory" test_id_is_checkout_independent

if (( fail > 0 )); then
  echo "$fail process export test(s) failed:" >&2
  printf ' - %s\n' "${failures[@]}" >&2
  exit 1
fi

echo "$pass process export tests passed"
