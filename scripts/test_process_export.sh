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

run_test "happy path export" test_happy_path_export
run_test "CLI dispatch" test_cli_dispatch

if (( fail > 0 )); then
  echo "$fail process export test(s) failed:" >&2
  printf ' - %s\n' "${failures[@]}" >&2
  exit 1
fi

echo "$pass process export tests passed"
