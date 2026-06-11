#!/usr/bin/env bash
# Tests for scripts/action_policy.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
POLICY="$REPO_DIR/scripts/action_policy.py"
CLI="$REPO_DIR/bin/beislid"

pass=0
fail=0
failures=()
TMP=""

setup_fixture() {
  TMP="$(mktemp -d)"
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

assert_decision() {
  local payload="$1" expected="$2"
  local actual
  actual="$(json_get "$payload" decision)"
  [[ "$actual" == "$expected" ]] || { note_fail "expected decision $expected, got $actual: $payload"; return 1; }
}

assert_contains_json_text() {
  local payload="$1" needle="$2"
  grep -qF -- "$needle" <<<"$payload" || { note_fail "expected JSON to contain: $needle"; return 1; }
}

test_supervised_read_allows() {
  local out
  out="$(python3 "$POLICY" evaluate --mode supervised-auto --action file.read)"
  assert_decision "$out" allow
  [[ "$(json_get "$out" classes.0)" == "read" ]] || { note_fail "read class missing"; return 1; }
}

test_git_status_is_read_only() {
  local out
  out="$(python3 "$POLICY" evaluate --mode unattended-auto --action git.status --sandbox-baseline non-default-branch)"
  assert_decision "$out" allow
  assert_contains_json_text "$out" '"read"'
}

test_strictest_class_wins() {
  local out
  out="$(python3 "$POLICY" evaluate --mode supervised-auto --action custom.cleanup --class read --class destructive)"
  assert_decision "$out" deny
  assert_contains_json_text "$out" '"class": "destructive"'
}

test_unknown_unattended_defaults_to_ask() {
  local out
  out="$(python3 "$POLICY" evaluate --mode unattended-auto --action custom.unknown --sandbox-baseline non-default-branch)"
  assert_decision "$out" ask
  assert_contains_json_text "$out" '"rule": "unknown_action"'
  assert_contains_json_text "$out" '"rule": "unclassified_action"'
}

test_action_override_can_allow_pr_reply() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "supervised-auto": {
      "actions": {
        "pr.review.reply": "allow"
      }
    }
  }
}
JSON
  out="$(python3 "$POLICY" evaluate --policy-file "$override" --mode supervised-auto --action pr.review.reply)"
  assert_decision "$out" allow
  assert_contains_json_text "$out" '"type": "action"'
}

test_policy_override_can_deny_workspace_write() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "supervised-auto": {
      "rules": {
        "workspace-write": "deny"
      }
    }
  }
}
JSON
  out="$(python3 "$POLICY" evaluate --policy-file "$override" --mode supervised-auto --action file.write)"
  assert_decision "$out" deny
}

test_unattended_requires_non_default_branch_by_default() {
  local out
  out="$(python3 "$POLICY" evaluate --mode unattended-auto --action file.read --sandbox-baseline none)"
  assert_decision "$out" ask
  assert_contains_json_text "$out" '"required_baseline": "non-default-branch"'
}

test_separate_worktree_satisfies_non_default_branch_baseline() {
  local out
  out="$(python3 "$POLICY" evaluate --mode unattended-auto --action file.read --sandbox-baseline separate-worktree)"
  assert_decision "$out" allow
}

test_uncommitted_changes_can_be_denied_by_override() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "unattended-auto": {
      "sandbox": {
        "on_uncommitted_changes": "deny"
      }
    }
  }
}
JSON
  out="$(python3 "$POLICY" evaluate --policy-file "$override" --mode unattended-auto --action file.read --sandbox-baseline non-default-branch --uncommitted-changes)"
  assert_decision "$out" deny
  assert_contains_json_text "$out" '"rule": "uncommitted_changes"'
}

test_secret_heuristic_adds_secret_bearing_class() {
  local out
  out="$(python3 "$POLICY" evaluate --mode unattended-auto --action gh.issue.view --command 'gh api -H "Authorization: Bearer $TOKEN"' --sandbox-baseline non-default-branch)"
  assert_decision "$out" deny
  assert_contains_json_text "$out" '"secret-bearing"'
}

test_benign_substring_is_not_secret_bearing() {
  local out
  out="$(python3 "$POLICY" evaluate --mode unattended-auto --action gh.issue.view --command 'python3 tokenizer.py' --sandbox-baseline non-default-branch)"
  assert_decision "$out" allow
  ! grep -qF '"secret-bearing"' <<<"$out" || { note_fail "benign substring inferred as secret-bearing"; return 1; }
}

test_action_override_can_allow_unattended_ask() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "unattended-auto": {
      "actions": {
        "custom.notify": "allow"
      }
    }
  }
}
JSON
  out="$(python3 "$POLICY" evaluate --policy-file "$override" --mode unattended-auto --action custom.notify --sandbox-baseline non-default-branch)"
  assert_decision "$out" allow
  assert_contains_json_text "$out" '"type": "action"'
}

test_action_override_can_allow_unprotected_deny() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "unattended-auto": {
      "actions": {
        "git.push": "allow"
      }
    }
  }
}
JSON
  out="$(python3 "$POLICY" evaluate --policy-file "$override" --mode unattended-auto --action git.push --sandbox-baseline non-default-branch)"
  assert_decision "$out" allow
}

test_action_override_cannot_allow_destructive_deny() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "supervised-auto": {
      "actions": {
        "shell.rm": "allow"
      }
    }
  }
}
JSON
  out="$(python3 "$POLICY" evaluate --policy-file "$override" --mode supervised-auto --action shell.rm)"
  assert_decision "$out" deny
  assert_contains_json_text "$out" '"rule": "protected_class_floor"'
}

test_compound_secret_assignment_is_secret_bearing() {
  local out
  out="$(python3 "$POLICY" evaluate --mode unattended-auto --action gh.issue.view --command 'export GITHUB_TOKEN=ghp_abc123' --sandbox-baseline non-default-branch)"
  assert_decision "$out" deny
  assert_contains_json_text "$out" '"secret-bearing"'
}

test_protected_floor_applies_at_ask_level() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "supervised-auto": {
      "actions": {
        "custom.fetch": "allow"
      }
    }
  }
}
JSON
  out="$(python3 "$POLICY" evaluate --policy-file "$override" --mode supervised-auto --action custom.fetch --class network-read --class secret-bearing)"
  assert_decision "$out" ask
  assert_contains_json_text "$out" '"applied": "ask"'
  assert_contains_json_text "$out" '"rule": "protected_class_floor"'
}

test_action_override_cannot_allow_inferred_secret_deny() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "unattended-auto": {
      "actions": {
        "gh.issue.view": "allow"
      }
    }
  }
}
JSON
  out="$(python3 "$POLICY" evaluate --policy-file "$override" --mode unattended-auto --action gh.issue.view --command 'export API_KEY=abc123' --sandbox-baseline non-default-branch)"
  assert_decision "$out" deny
  assert_contains_json_text "$out" '"rule": "protected_class_floor"'
}

test_validate_valid_policy_summary() {
  local override out
  override="$TMP/policy.json"
  cat >"$override" <<'JSON'
{
  "modes": {
    "unattended-auto": {
      "sandbox": {
        "minimum": "separate-worktree"
      },
      "unknown_action": "ask"
    }
  }
}
JSON
  out="$(python3 "$POLICY" validate --policy-file "$override")"
  [[ "$(json_get "$out" status)" == "ok" ]] || { note_fail "policy summary did not report ok"; return 1; }
  assert_contains_json_text "$out" '"minimum": "separate-worktree"'
  assert_contains_json_text "$out" '"known_action_count"'
}

test_validate_rejects_malformed_mode_policy() {
  local override err
  override="$TMP/policy.json"
  err="$TMP/err.txt"
  cat >"$override" <<'JSON'
{
  "modes": {
    "supervised-auto": "bad"
  }
}
JSON
  if python3 "$POLICY" validate --policy-file "$override" >"$TMP/out.txt" 2>"$err"; then
    note_fail "expected malformed policy validation to fail"
    return 1
  fi
  grep -qF 'policy.modes.supervised-auto must be an object' "$err" || { note_fail "expected malformed mode error"; return 1; }
  ! grep -qF 'Traceback' "$err" || { note_fail "unexpected traceback"; return 1; }
}

test_validate_rejects_invalid_policy() {
  local override err
  override="$TMP/policy.json"
  err="$TMP/err.txt"
  cat >"$override" <<'JSON'
{
  "modes": {
    "unattended-auto": {
      "rules": {
        "git-remote": "maybe"
      }
    }
  }
}
JSON
  if python3 "$POLICY" validate --policy-file "$override" >"$TMP/out.txt" 2>"$err"; then
    note_fail "expected invalid policy validation to fail"
    return 1
  fi
  grep -qF 'invalid decision' "$err" || { note_fail "expected invalid decision error"; return 1; }
}

test_cli_dispatch() {
  local out
  out="$(BEISLID_HOME="$REPO_DIR" "$CLI" action-policy evaluate --mode supervised-auto --action git.push)"
  assert_decision "$out" ask
  assert_contains_json_text "$out" '"action": "git.push"'
}

run_test "supervised read allows" test_supervised_read_allows
run_test "git status is read-only" test_git_status_is_read_only
run_test "strictest class wins" test_strictest_class_wins
run_test "unknown unattended asks" test_unknown_unattended_defaults_to_ask
run_test "action override allows PR reply" test_action_override_can_allow_pr_reply
run_test "policy override denies workspace write" test_policy_override_can_deny_workspace_write
run_test "unattended requires non-default branch" test_unattended_requires_non_default_branch_by_default
run_test "separate worktree satisfies baseline" test_separate_worktree_satisfies_non_default_branch_baseline
run_test "uncommitted changes override can deny" test_uncommitted_changes_can_be_denied_by_override
run_test "secret heuristic adds class" test_secret_heuristic_adds_secret_bearing_class
run_test "benign substring is not secret-bearing" test_benign_substring_is_not_secret_bearing
run_test "compound secret assignment is secret-bearing" test_compound_secret_assignment_is_secret_bearing
run_test "protected floor applies at ask level" test_protected_floor_applies_at_ask_level
run_test "action override allows unattended ask" test_action_override_can_allow_unattended_ask
run_test "action override allows unprotected deny" test_action_override_can_allow_unprotected_deny
run_test "action override cannot allow destructive deny" test_action_override_cannot_allow_destructive_deny
run_test "action override cannot allow inferred secret deny" test_action_override_cannot_allow_inferred_secret_deny
run_test "validate valid policy summary" test_validate_valid_policy_summary
run_test "validate rejects malformed mode policy" test_validate_rejects_malformed_mode_policy
run_test "validate rejects invalid policy" test_validate_rejects_invalid_policy
run_test "CLI dispatch" test_cli_dispatch

if (( fail > 0 )); then
  echo "$fail action policy test(s) failed:" >&2
  printf ' - %s\n' "${failures[@]}" >&2
  exit 1
fi

echo "$pass action policy tests passed"
