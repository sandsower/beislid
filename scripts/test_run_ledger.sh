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
    if isinstance(cur, list):
        cur = cur[int(part)]
    else:
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
  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 15 --ticket-title 'Durable ledger' --branch feature/ledger)"
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
  [[ "$(json_get "$run_dir/run.json" kind)" == "run-ledger-v1" ]] || { note_fail "run kind not recorded"; return 1; }
  [[ "$(json_get "$run_dir/run.json" flow)" == "kickoff" ]] || { note_fail "run flow not recorded"; return 1; }
  [[ "$(json_get "$run_dir/run.json" status)" == "running" ]] || { note_fail "run should start running"; return 1; }
  [[ "$(json_get "$run_dir/run.json" ticket.id)" == "15" ]] || { note_fail "ticket id not recorded"; return 1; }

  event_payload="$TMP/event.json"
  printf '{"title":"ticket loaded","message":"Authorization: Bearer abc123","token":"secret-token-value"}\n' > "$event_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" event --run-id "$run_id" --type ticket_snapshot --json-file "$event_payload") >/dev/null
  assert_contains "$run_dir/events.jsonl" '"type": "ticket_snapshot"'
  assert_contains "$run_dir/transcript.md" 'ticket_snapshot'
  if grep -q -e 'secret-token-value' -e 'Bearer abc123' "$run_dir/transcript.md" "$run_dir/events.jsonl"; then
    note_fail "ledger should redact secret-looking values"
    return 1
  fi

  checkpoint_payload="$TMP/checkpoint.json"
  printf '{"next":"implement"}\n' > "$checkpoint_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" checkpoint --run-id "$run_id" --flow kickoff --name kickoff_context_ready --json-file "$checkpoint_payload" --resume-hint 'continue with implementation planning') >/dev/null
  assert_file "$run_dir/checkpoints/kickoff_context_ready.json"
  assert_contains "$run_dir/checkpoints/kickoff_context_ready.json" 'resume_hint'
  [[ "$(json_get "$run_dir/run.json" latest_checkpoint.name)" == "kickoff_context_ready" ]] || { note_fail "latest checkpoint not recorded"; return 1; }
  [[ "$(json_get "$run_dir/run.json" resume_hint)" == "continue with implementation planning" ]] || { note_fail "resume hint not recorded"; return 1; }

  local gate_payload="$TMP/gate.json"
  printf '{"gate":{"name":"validate-skills"},"status":"pass","authorization":"Bearer abc123"}\n' > "$gate_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" gate --run-id "$run_id" --flow kickoff --name validate-skills --scope repo --envelope-file "$gate_payload") >/dev/null
  assert_file "$run_dir/artifacts/gates/repo/validate-skills/1/envelope.json"
  [[ "$(json_get "$run_dir/run.json" artifacts.0.kind)" == "gate" ]] || { note_fail "gate artifact bookkeeping not recorded"; return 1; }
  [[ "$(json_get "$run_dir/run.json" logs.0.kind)" == "gate" ]] || { note_fail "gate log bookkeeping not recorded"; return 1; }
  [[ "$(json_get "$run_dir/run.json" logs.0.path)" == "$run_dir/artifacts/gates/repo/validate-skills/1/envelope.json" ]] || { note_fail "gate log path not recorded"; return 1; }
  if grep -q 'Bearer abc123' "$run_dir/artifacts/gates/repo/validate-skills/1/envelope.json" "$run_dir/events.jsonl"; then
    note_fail "gate logs/events should redact auth values"
    return 1
  fi

  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" interrupt --run-id "$run_id" --flow kickoff --reason human_interrupt --resume-hint 'resume at approval boundary') >/dev/null
  [[ "$(json_get "$run_dir/run.json" status)" == "interrupted" ]] || { note_fail "run should be interrupted"; return 1; }

  report="$TMP/report.md"
  printf '# Final report\n\nDone.\n' > "$report"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" finalize --run-id "$run_id" --flow kickoff --status completed --report-file "$report") >/dev/null
  assert_file "$run_dir/final-report.md"
  [[ "$(json_get "$run_dir/run.json" status)" == "completed" ]] || { note_fail "run should be completed"; return 1; }

  resume_out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" resume --flow kickoff --ticket-id 15 --branch feature/ledger --include-completed)"
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
  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" BEISLID_HOME="$REPO_DIR" "$CLI" run-ledger init --skill implement --flow implement --ticket-id 15 --ticket-title 'CLI dispatch' --branch feature/ledger)"
  python3 - <<'PY' "$out"
import json, sys
payload = json.loads(sys.argv[1])
assert payload['run_id']
assert payload['run_dir']
PY
}

test_cli_dispatch_requires_python3() {
  local state="$TMP/state" path_dir err status
  state="$TMP/state"
  path_dir="$TMP/no-python"
  mkdir -p "$path_dir"
  ln -s "$(command -v bash)" "$path_dir/bash"
  ln -s "$(command -v dirname)" "$path_dir/dirname"
  ln -s "$(command -v readlink)" "$path_dir/readlink"
  err="$TMP/err.txt"
  if cd "$TMP/repo" && BEISLID_STATE_DIR="$state" PATH="$path_dir" BEISLID_HOME="$REPO_DIR" "$CLI" run-ledger init --skill implement --flow implement --ticket-id 15 --ticket-title 'CLI dispatch' --branch feature/ledger >"$TMP/out.txt" 2>"$err"; then
    note_fail "expected run-ledger dispatch to fail without python3"
    return 1
  else
    status=$?
  fi
  [[ "$status" == "1" ]] || { note_fail "expected exit status 1, got $status"; return 1; }
  grep -qF 'error: beislid run-ledger requires python3' "$err" || { note_fail "expected python3 guard error"; return 1; }
}

test_run_ledger_skill_examples_consistency_check() {
  local checker="$REPO_DIR/scripts/check_run_ledger_skill_examples_consistency.py" broken_root broken_err
  if ! (cd "$REPO_DIR" && python3 "$checker") >/dev/null; then
    note_fail "baseline run-ledger checker should pass on the repo"
    return 1
  fi

  broken_root="$TMP/broken-run-ledger-check"
  broken_err="$TMP/broken-run-ledger-check.err"
  mkdir -p "$broken_root/scripts" "$broken_root/skills/kickoff"
  cp "$REPO_DIR/scripts/run_ledger.py" "$broken_root/scripts/run_ledger.py"
  cat > "$broken_root/skills/kickoff/SKILL.md" <<'EOF'
---
name: kickoff
description: broken example
---
For durable evidence, best-effort `beislid run-ledger init/resume ... --flow kickoff`.
EOF

  if python3 "$checker" --root "$broken_root" >"$TMP/broken-run-ledger-check.out" 2>"$broken_err"; then
    note_fail "run-ledger skill-example checker should reject init/resume prose"
    return 1
  fi
  assert_contains "$broken_err" 'split `init/resume`'

  local broken_cli_root="$TMP/broken-run-ledger-cli" broken_cli_err="$TMP/broken-run-ledger-cli.err"
  mkdir -p "$broken_cli_root/scripts" "$broken_cli_root/skills/kickoff"
  cp "$REPO_DIR/scripts/run_ledger.py" "$broken_cli_root/scripts/run_ledger.py"
  python3 - <<'PY' "$broken_cli_root/scripts/run_ledger.py"
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace('    checkpoint_p.add_argument("--name", required=True)\n', '', 1)
path.write_text(text, encoding="utf-8")
PY
  cat > "$broken_cli_root/skills/kickoff/SKILL.md" <<'EOF'
---
name: kickoff
description: cli regression
---
EOF

  if python3 "$checker" --root "$broken_cli_root" >"$TMP/broken-run-ledger-cli.out" 2>"$broken_cli_err"; then
    note_fail "run-ledger skill-example checker should reject checkpoint parser drift"
    return 1
  fi
  assert_contains "$broken_cli_err" 'checkpoint parser missing required flag --name'
}

test_resume_ignores_completed_without_flag() {
  local state="$TMP/state" out completed_id interrupted_id resume_out report="$TMP/report.md"
  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 15 --ticket-title 'Completed run' --branch feature/ledger)"
  completed_id="$(python3 - <<'PY' "$out"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"
  printf '# Final report\n\nDone.\n' > "$report"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" finalize --run-id "$completed_id" --flow kickoff --status completed --report-file "$report") >/dev/null

  local unexpected_out="$TMP/beislid-resume-unexpected.out"
  if (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" resume --flow kickoff --ticket-id 15 --branch feature/ledger) >"$unexpected_out" 2>/dev/null; then
    note_fail "resume should ignore completed runs unless --include-completed"
    return 1
  fi

  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 15 --ticket-title 'Interrupted run' --branch feature/ledger)"
  interrupted_id="$(python3 - <<'PY' "$out"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" interrupt --run-id "$interrupted_id" --flow kickoff --reason human_interrupt --resume-hint 'continue after interruption') >/dev/null

  resume_out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" resume --flow kickoff --ticket-id 15 --branch feature/ledger)"
  python3 - <<'PY' "$resume_out" "$interrupted_id"
import json, sys
payload = json.loads(sys.argv[1])
expected = sys.argv[2]
assert payload['run_id'] == expected, payload
assert payload['status'] == 'interrupted', payload
assert payload['resume_hint'] == 'continue after interruption', payload
PY
}

test_rejects_unsafe_run_id() {
  local state="$TMP/state"
  local unsafe_out="$TMP/beislid-unsafe-run-id.out"
  local unsafe_err="$TMP/beislid-unsafe-run-id.err"
  if (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --run-id '../escape') >"$unsafe_out" 2>"$unsafe_err"; then
    note_fail "unsafe run id should be rejected"
    return 1
  fi
  if [[ -e "$state/runs/escape" || -e "$state/escape" ]]; then
    note_fail "unsafe run id wrote outside the run root"
    return 1
  fi
  assert_contains "$unsafe_err" 'invalid run id'
}

test_legacy_active_resume_without_flow() {
  local state="$TMP/state" out run_id run_dir repo_hash legacy_dir resume_out
  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 15 --ticket-title 'Legacy run' --branch feature/ledger)"
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
  repo_hash="$(basename "$(dirname "$run_dir")")"
  legacy_dir="$state/runs/$repo_hash/$run_id"
  mkdir -p "$(dirname "$legacy_dir")"
  mv "$run_dir" "$legacy_dir"
  python3 - <<'PY' "$legacy_dir/run.json"
import json, sys
path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    payload = json.load(f)
payload['status'] = 'active'
payload['paths']['run_dir'] = path.rsplit('/', 1)[0]
with open(path, 'w', encoding='utf-8') as f:
    json.dump(payload, f, indent=2, sort_keys=True)
    f.write('\n')
PY

  resume_out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" resume --ticket-id 15 --branch feature/ledger)"
  python3 - <<'PY' "$resume_out" "$run_id"
import json, sys
payload = json.loads(sys.argv[1])
expected = sys.argv[2]
assert payload['run_id'] == expected, payload
assert payload['status'] == 'active', payload
PY
}

test_policy_secret_parity_redaction() {
  python3 - "$REPO_DIR/scripts/action_policy.py" "$LEDGER" <<'PY'
import importlib.util
import pathlib
import sys


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

policy = load_module("action_policy", pathlib.Path(sys.argv[1]))
ledger = load_module("run_ledger", pathlib.Path(sys.argv[2]))

cases = [
    ("assignment token", "TOKEN=token_value", "TOKEN=[REDACTED]"),
    ("assignment secret", "secret: secret_value", "secret=[REDACTED]"),
    ("assignment password", "PASSWORD=password_value", "PASSWORD=[REDACTED]"),
    ("assignment api key", "API_KEY=api_value", "API_KEY=[REDACTED]"),
    ("assignment private key", "PRIVATE_KEY=private_value", "PRIVATE_KEY=[REDACTED]"),
    ("assignment auth header", "auth_header: header_value", "auth_header=[REDACTED]"),
    ("bearer auth", "Authorization: Bearer bearer_value", "Authorization: Bearer [REDACTED]"),
    ("env token", "deploy with $TOKEN", "deploy with [REDACTED]"),
    ("env github token", "deploy with ${GITHUB_TOKEN}", "deploy with [REDACTED]"),
]

errors = []
for name, sample, expected in cases:
    if not policy.infer_secret_bearing("", sample, {}):
        errors.append(f"policy did not flag {name}: {sample!r}")
    actual = ledger.redact_text(sample)
    if actual != expected:
        errors.append(f"ledger redaction mismatch for {name}: expected {expected!r}, got {actual!r}")

if errors:
    for error in errors:
        print(error, file=sys.stderr)
    raise SystemExit(1)
PY
}


test_compound_secret_redaction() {
  local state="$TMP/state" out run_id run_dir event_payload
  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 15 --ticket-title 'Compound redaction' --branch feature/redaction)"
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

  event_payload="$TMP/compound-event.json"
  python3 - <<'PY' "$event_payload"
import json, sys
payload = {
    "message": "GITHUB_TOKEN=compound_text_value\nSECRET_KEY=compound_key_value\ndb_password: compound_password_value\nprivate_key=compound_private_value\nauth_header: compound_auth_header_value",
    "github_token": "compound_json_value",
    "private_key": "compound_private_json_value",
    "auth_header": "compound_auth_header_json_value",
    "notes": "tokenizer and passwordless should remain visible",
    "z_large": "x" * 2500,
    "z_tail": "uncapped_tail_marker",
}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(payload, f)
PY
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" event --run-id "$run_id" --flow kickoff --type ticket_snapshot --json-file "$event_payload") >/dev/null

  if grep -q -e 'compound_text_value' -e 'compound_key_value' -e 'compound_password_value' -e 'compound_json_value' "$run_dir/events.jsonl" "$run_dir/transcript.md"; then
    note_fail "compound secret-looking values should be redacted"
    return 1
  fi
  assert_contains "$run_dir/events.jsonl" 'tokenizer'
  assert_contains "$run_dir/events.jsonl" 'passwordless'
  assert_contains "$run_dir/transcript.md" 'tokenizer'
  assert_contains "$run_dir/transcript.md" 'passwordless'
  assert_contains "$run_dir/events.jsonl" 'uncapped_tail_marker'
  if grep -qF 'uncapped_tail_marker' "$run_dir/transcript.md"; then
    note_fail "transcript summary should keep its length cap"
    return 1
  fi
}

test_dashboard_active_runs() {
  local state="$TMP/state" out1 out2 run1_id run2_id dash_out dash_json gate_payload cp_payload dash_file
  dash_file="$TMP/dash_out.txt"

  out1="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 25 --ticket-title 'Dashboard run 1' --branch feature/dash1)"
  run1_id="$(python3 - <<'PY' "$out1"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"

  cp_payload="$TMP/cp.json"
  printf '{"step":"done"}\n' > "$cp_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" checkpoint --run-id "$run1_id" --flow kickoff --name kickoff_context_ready --json-file "$cp_payload" --resume-hint 'proceed') >/dev/null

  gate_payload="$TMP/gate.json"
  printf '{"gate":{"name":"validate-skills"},"status":"pass"}\n' > "$gate_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" gate --run-id "$run1_id" --flow kickoff --name validate-skills --scope repo --envelope-file "$gate_payload") >/dev/null

  out2="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill implement --flow implement --ticket-id 26 --ticket-title 'Dashboard run 2' --branch feature/dash2)"
  run2_id="$(python3 - <<'PY' "$out2"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" interrupt --run-id "$run2_id" --flow implement --reason 'human approval required') >/dev/null

  printf '{"gate":{"name":"install-integration-tests"},"status":"fail","environment_failure":true}\n' > "$gate_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" gate --run-id "$run2_id" --flow implement --name install-integration-tests --scope repo --envelope-file "$gate_payload") >/dev/null

  cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard > "$dash_file"
  assert_contains "$dash_file" 'Beislið Run Dashboard'
  assert_contains "$dash_file" '2 run(s)'
  assert_contains "$dash_file" '1 running'
  assert_contains "$dash_file" '1 interrupted'
  assert_contains "$dash_file" '[INTERRUPTED]'
  assert_contains "$dash_file" '[RUNNING]'
  assert_contains "$dash_file" 'human approval required'
  assert_contains "$dash_file" 'Dashboard run 1'
  assert_contains "$dash_file" 'Dashboard run 2'

  dash_json="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard --json)"
  python3 - <<'PY' "$dash_json"
import json, sys
data = json.loads(sys.argv[1])
assert data['total'] == 2, f'expected 2 runs, got {data["total"]}'
assert len(data['runs']) == 2
run_statuses = {r['run_id']: r['status'] for r in data['runs']}
assert 'interrupted' in run_statuses.values(), 'expected at least one interrupted run'
assert 'running' in run_statuses.values(), 'expected at least one running run'
for r in data['runs']:
    if r['status'] == 'interrupted':
        assert 'interruption' in r, 'interrupted run missing interruption details'
        assert r['interruption']['reason'] == 'human approval required'
PY
}

test_dashboard_flow_filter() {
  local state="$TMP/state" out1 out2 run1_id run2_id dash_file
  dash_file="$TMP/dash_ff.txt"

  out1="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 25 --ticket-title 'Flow filter test' --branch feature/ff)"
  run1_id="$(python3 - <<'PY' "$out1"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"

  out2="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill implement --flow implement --ticket-id 26 --ticket-title 'Other flow' --branch feature/ff2)"
  run2_id="$(python3 - <<'PY' "$out2"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"

  cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard --flow kickoff > "$dash_file"
  assert_contains "$dash_file" '1 run(s)'
  assert_contains "$dash_file" 'Flow filter test'
  if grep -q 'Other flow' "$dash_file"; then
    note_fail "flow filter should exclude implement runs"
    return 1
  fi
}

test_dashboard_empty() {
  local state="$TMP/state" dash_file dash_json
  dash_file="$TMP/dash_empty.txt"

  cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard > "$dash_file"
  assert_contains "$dash_file" 'No matching runs found'

  dash_json="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard --json)"
  python3 - <<'PY' "$dash_json"
import json, sys
data = json.loads(sys.argv[1])
assert data['total'] == 0, f'expected 0 runs, got {data["total"]}'
assert data['runs'] == []
PY
}

test_dashboard_with_completed() {
  local state="$TMP/state" out1 out2 run1_id run2_id report dash_file dash_all_file
  dash_file="$TMP/dash_comp.txt"
  dash_all_file="$TMP/dash_comp_all.txt"

  out1="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 25 --ticket-title 'Completed run' --branch feature/comp)"
  run1_id="$(python3 - <<'PY' "$out1"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"
  report="$TMP/report.md"
  printf '# Done\n' > "$report"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" finalize --run-id "$run1_id" --flow kickoff --status completed --report-file "$report") >/dev/null

  out2="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill implement --flow implement --ticket-id 26 --ticket-title 'Running run' --branch feature/comp2)"
  run2_id="$(python3 - <<'PY' "$out2"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"

  cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard > "$dash_file"
  assert_contains "$dash_file" '1 run(s)'
  if grep -q 'Completed run' "$dash_file"; then
    note_fail "dashboard without --all should exclude completed runs"
    return 1
  fi

  cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard --all > "$dash_all_file"
  assert_contains "$dash_all_file" '2 run(s)'
  assert_contains "$dash_all_file" 'Completed run'
  assert_contains "$dash_all_file" 'Running run'
}

test_dashboard_gate_classification() {
  local state="$TMP/state" out run_id dash_file gate_payload
  dash_file="$TMP/dash_gates.txt"

  out="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" init --skill kickoff --flow kickoff --ticket-id 25 --ticket-title 'Gate test' --branch feature/gates)"
  run_id="$(python3 - <<'PY' "$out"
import json, sys
print(json.loads(sys.argv[1])['run_id'])
PY
)"

  gate_payload="$TMP/gate.json"
  printf '{"gate":{"name":"code-fail"},"status":"fail","classification":"code_failure"}\n' > "$gate_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" gate --run-id "$run_id" --flow kickoff --name code-fail --scope repo --envelope-file "$gate_payload") >/dev/null

  printf '{"gate":{"name":"env-fail"},"status":"fail","environment_failure":true}\n' > "$gate_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" gate --run-id "$run_id" --flow kickoff --name env-fail --scope repo --envelope-file "$gate_payload") >/dev/null

  printf '{"gate":{"name":"skipped"},"status":"skip"}\n' > "$gate_payload"
  (cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" gate --run-id "$run_id" --flow kickoff --name skipped --scope repo --envelope-file "$gate_payload") >/dev/null

  cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard > "$dash_file"
  assert_contains "$dash_file" '[CODE]'
  assert_contains "$dash_file" '[ENV]'
  assert_contains "$dash_file" 'code-fail'
  assert_contains "$dash_file" 'env-fail'
  assert_contains "$dash_file" 'skipped'

  dash_json="$(cd "$TMP/repo" && BEISLID_STATE_DIR="$state" python3 "$LEDGER" dashboard --json)"
  python3 - <<'PY' "$dash_json"
import json, sys
data = json.loads(sys.argv[1])
assert data['total'] == 1
gates = data['runs'][0].get('gates', [])
classifications = {g['name']: g.get('classification') for g in gates}
assert classifications.get('code-fail') == 'code_failure', f'unexpected: {classifications}'
assert classifications.get('env-fail') == 'environment_failure', f'unexpected: {classifications}'
assert classifications.get('skipped') is None, f'skip should have no classification: {classifications}'
PY
}
run_test "init/event/checkpoint/finalize/resume" test_init_event_checkpoint_finalize_resume
run_test "resume ignores completed without flag" test_resume_ignores_completed_without_flag
run_test "rejects unsafe run id" test_rejects_unsafe_run_id
run_test "legacy active resume without flow" test_legacy_active_resume_without_flow
run_test "policy secret parity redaction" test_policy_secret_parity_redaction
run_test "compound secret redaction" test_compound_secret_redaction
run_test "beislid CLI dispatch" test_cli_dispatch
run_test "CLI dispatch requires python3" test_cli_dispatch_requires_python3
run_test "run-ledger skill-example consistency check" test_run_ledger_skill_examples_consistency_check
run_test "dashboard active runs" test_dashboard_active_runs
run_test "dashboard flow filter" test_dashboard_flow_filter
run_test "dashboard empty" test_dashboard_empty
run_test "dashboard with completed" test_dashboard_with_completed
run_test "dashboard gate classification" test_dashboard_gate_classification

printf '\n%d passed, %d failed\n' "$pass" "$fail"
if (( fail > 0 )); then
  printf 'Failures:\n' >&2
  printf '  - %s\n' "${failures[@]}" >&2
  exit 1
fi
