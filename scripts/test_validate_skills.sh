#!/usr/bin/env bash
# Tests for scripts/validate_skills.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_SCRIPT="$REPO_DIR/scripts/validate_skills.py"

pass=0
fail=0
failures=()
TMP=""

note_fail() {
  echo "    $1" >&2
}

setup_fixture() {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/scripts" "$TMP/skills"
  cp "$SOURCE_SCRIPT" "$TMP/scripts/validate_skills.py"
}

teardown() {
  [[ -n "${TMP:-}" ]] && rm -rf "$TMP"
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

write_skill() {
  local skill="$1" body="$2"
  mkdir -p "$TMP/skills/$skill"
  printf '%s' "$body" > "$TMP/skills/$skill/SKILL.md"
}

run_validator() {
  (cd "$TMP" && python3 "$TMP/scripts/validate_skills.py")
}

assert_ok() {
  local out err
  out="$TMP/out.txt"
  err="$TMP/err.txt"
  if ! run_validator >"$out" 2>"$err"; then
    note_fail "validator should have passed"
    cat "$err" >&2
    return 1
  fi
  grep -qF 'ok: 1 skills validated' "$out" || { note_fail "expected success banner"; return 1; }
}

test_accepts_frontmatter_without_terminal_newline() {
  write_skill foo $'---\nname: foo\ndescription: "plain description"\n---'
  assert_ok
}

test_accepts_quoted_name_with_comment_and_block_description() {
  write_skill foo $'---\nname: "foo" # keep this comment\ndescription: >\n  wrapped\n  description\n---\n'
  assert_ok
}

test_preserves_indented_frontmatter_delimiter_inside_block_scalar() {
  write_skill foo $'---\nname: foo\ndescription: >\n  keep this line\n    ---\n  and this line too\n---\n'
  assert_ok
}

run_test "frontmatter without terminal newline" test_accepts_frontmatter_without_terminal_newline
run_test "quoted name comment and block description" test_accepts_quoted_name_with_comment_and_block_description
run_test "indented block scalar delimiter preserved" test_preserves_indented_frontmatter_delimiter_inside_block_scalar

printf '\n%d passed, %d failed\n' "$pass" "$fail"
if (( fail > 0 )); then
  printf 'Failures:\n' >&2
  printf '  - %s\n' "${failures[@]}" >&2
  exit 1
fi
