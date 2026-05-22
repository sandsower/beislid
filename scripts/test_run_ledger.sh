#!/usr/bin/env bash
# Tests for scripts/run_ledger.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LEDGER="$REPO_DIR/scripts/run_ledger.py"
CLI="$REPO_DIR/bin/beislid"

pass=0
fail=0
failures=()
TMP=""

note_fail() {
  echo "    $1" >&2
}

setup_fixture() {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/repo"
  git -C "$TMP/repo" init -q
  git -C "$TMP/repo" config user.email test@example.invalid
  git -C "$TMP/repo" config user.name Test
  printf 'hello\n' > "$TMP/repo/README.md"
  git -C "$TMP/repo" add README.md
  git -C "$TMP/repo" commit -q -m init
}

teardown() {
  [[ -n "${TMP:-}" ]] && rm -rf "$TMP"
}

json_get() {
  python3 - <<'PY' "$1" "$2"
import json, sys
path, dotted = sys.argv[1:]
data = json.load(open(path, encoding='utf-8'))
cur = data
for part in dotted.split('.'):
    cur = cur[part]
print(cur)
PY
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

assert_file() {
  local path="$1"
  [[ -f "$path" ]] || { note_fail "expected file: $path"; return 1; }
}

assert_dir() {
  local path="$1"
  [[ -d "$path" ]] || { note_fail "expected dir: $path"; return 1; }
}

assert_contains() {
  local path="$1" needle="$2"
  grep -qF -- "$needle" "$path" || { note_fail "expected $path to contain: $needle"; return 1; }
}

test_init_event_checkpoint_finalize_resume() {
  local state="$TMP/state" out run_id run_dir event_payload checkpoint_payload report resume_out
  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --ticket-id 15 --ticket-title 'Durable ledger' --branch feature/ledger)"
  run_id="$(python3 - <<'PY' "$out"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"
  run_dir="$(python3 - <<'PY' "$out"
import json, sys
print(json.loads(sys.argv[1])['run_dir'])
PY
)"

  [[ "$run_id" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}$ ]] || { note_fail "unexpected run id: $run_id"; return 1; }
  assert_dir "$run_dir"
  assert_dir "$run_dir/artifacts"
  assert_dir "$run_dir/logs"
  assert_dir "$run_dir/checkpoints"
  assert_file "$run_dir/run.json"
  assert_file "$run_dir/events.jsonl"
  assert_file "$run_dir/transcript.md"
  [[ "$(json_get "$run_dir/run.json" status)" == "active" ]] || { note_fail "run should start active"; return 1; }
  [[ "$(json_get "$run_dir/run.json" ticket.id)" == "15" ]] || { note_fail "ticket id not recorded"; return 1; }

  event_payload="$TMP/event.json"
  printf '{"title":"ticket loaded","token":"secret-token-value"}\n' > "$event_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" event --run-id "$run_id" --type ticket_snapshot --json-file "$event_payload") >/dev/null
  assert_contains "$run_dir/events.jsonl" '"type": "ticket_snapshot"'
  assert_contains "$run_dir/transcript.md" 'ticket_snapshot'
  if grep -q 'secret-token-value' "$run_dir/transcript.md" "$run_dir/events.jsonl"; then
    note_fail "ledger should redact secret-looking values"
    return 1
  fi

  checkpoint_payload="$TMP/checkpoint.json"
  printf '{"next":"implement"}\n' > "$checkpoint_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" checkpoint --run-id "$run_id" --name kickoff_context_ready --json-file "$checkpoint_payload") >/dev/null
  assert_file "$run_dir/checkpoints/kickoff_context_ready.json"
  [[ "$(json_get "$run_dir/run.json" latest_checkpoint.name)" == "kickoff_context_ready" ]] || { note_fail "latest checkpoint not recorded"; return 1; }

  local gate_payload="$TMP/gate.json"
  printf '{"gate":{"name":"validate-skills"},"status":"pass","authorization":"Bearer abc123"}\n' > "$gate_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" gate --run-id "$run_id" --name validate-skills --envelope-file "$gate_payload") >/dev/null
  assert_file "$run_dir/logs/validate-skills.json"
  if grep -q 'Bearer abc123' "$run_dir/logs/validate-skills.json" "$run_dir/events.jsonl"; then
    note_fail "gate logs/events should redact auth values"
    return 1
  fi

  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" interrupt --run-id "$run_id" --reason human_interrupt) >/dev/null
  [[ "$(json_get "$run_dir/run.json" status)" == "interrupted" ]] || { note_fail "run should be interrupted"; return 1; }

  report="$TMP/report.md"
  printf '# Final report\n\nDone.\n' > "$report"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" finalize --run-id "$run_id" --status completed --report-file "$report") >/dev/null
  assert_file "$run_dir/final-report.md"
  [[ "$(json_get "$run_dir/run.json" status)" == "completed" ]] || { note_fail "run should be completed"; return 1; }

  resume_out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" resume --ticket-id 15 --branch feature/ledger --include-completed)"
  python3 - <<'PY' "$resume_out" "$run_id"
import json, sys
payload = json.loads(sys.argv[1])
expected = sys.argv[2]
assert payload['run_id'] == expected, payload
assert payload['status'] == 'completed', payload
PY
}

test_cli_dispatch() {
  local state="$TMP/state" out
  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" BEISLID_HOME="$REPO_DIR" "$CLI" run-ledger init --skill implement --ticket-id 15 --ticket-title 'CLI dispatch' --branch feature/ledger)"
  python3 - <<'PY' "$out"
import json, sys
payload = json.loads(sys.argv[1])
assert payload['run_id']
assert payload['run_dir']
PY
}

run_test "init/event/checkpoint/finalize/resume" test_init_event_checkpoint_finalize_resume
run_test "beislid CLI dispatch" test_cli_dispatch

printf '\n%d passed, %d failed\n' "$pass" "$fail"
if (( fail > 0 )); then
  printf 'Failures:\n' >&2
  printf '  - %s\n' "${failures[@]}" >&2
  exit 1
fi
