#!/usr/bin/env bash
# Tests for scripts/bump-version.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_SCRIPT="$REPO_DIR/scripts/bump-version.sh"

pass=0
fail=0
failures=()
TMP=""

note_fail() {
  echo "    $1" >&2
}

setup_fixture() {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/.claude-plugin" "$TMP/scripts"
  cp "$SOURCE_SCRIPT" "$TMP/scripts/bump-version.sh"
  chmod +x "$TMP/scripts/bump-version.sh"
  write_versions "0.1.0" "0.1.0"
}

teardown() {
  [[ -n "${TMP:-}" ]] && rm -rf "$TMP"
}

write_versions() {
  local pkg_version="$1" plugin_version="$2"
  python3 - <<'PY' "$TMP/package.json" "$pkg_version" "$TMP/.claude-plugin/plugin.json" "$plugin_version"
import json, sys
pkg_path, pkg_version, plugin_path, plugin_version = sys.argv[1:]
for path, version in [(pkg_path, pkg_version), (plugin_path, plugin_version)]:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({"name": "fixture", "version": version}, f, indent=2)
        f.write("\n")
PY
}

json_version() {
  python3 - <<'PY' "$1"
import json, sys
print(json.load(open(sys.argv[1], encoding='utf-8'))['version'])
PY
}

assert_versions() {
  local expected="$1"
  local pkg_v plugin_v
  pkg_v="$(json_version "$TMP/package.json")"
  plugin_v="$(json_version "$TMP/.claude-plugin/plugin.json")"
  if [[ "$pkg_v" != "$expected" ]]; then
    note_fail "expected package.json version $expected, got $pkg_v"
    return 1
  fi
  if [[ "$plugin_v" != "$expected" ]]; then
    note_fail "expected plugin.json version $expected, got $plugin_v"
    return 1
  fi
}

run_ok() {
  local bump="$1" expected="$2" out
  out="$(cd "$TMP" && ./scripts/bump-version.sh "$bump")"
  if [[ "$out" != "$expected" ]]; then
    note_fail "expected stdout '$expected' for bump '$bump', got '$out'"
    return 1
  fi
  assert_versions "$expected"
}

run_fails() {
  local bump="$1"
  if (cd "$TMP" && ./scripts/bump-version.sh "$bump" >/tmp/beislid-bump-test.out 2>/tmp/beislid-bump-test.err); then
    note_fail "expected bump '$bump' to fail"
    return 1
  fi
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

test_patch() { run_ok patch 0.1.1; }
test_minor() { run_ok minor 0.2.0; }
test_major() { run_ok major 1.0.0; }
test_explicit_version() { run_ok 2.3.4 2.3.4; }

test_refuses_manifest_drift() {
  write_versions 0.1.0 0.1.1
  run_fails patch
}

test_refuses_invalid_current_version() {
  write_versions dev dev
  run_fails patch
}

test_refuses_invalid_bump_kind() {
  run_fails nope
}

run_test "patch bump" test_patch
run_test "minor bump" test_minor
run_test "major bump" test_major
run_test "explicit version" test_explicit_version
run_test "manifest drift refused" test_refuses_manifest_drift
run_test "invalid current version refused" test_refuses_invalid_current_version
run_test "invalid bump kind refused" test_refuses_invalid_bump_kind

printf '\n%d passed, %d failed\n' "$pass" "$fail"
if (( fail > 0 )); then
  printf 'Failures:\n' >&2
  printf '  - %s\n' "${failures[@]}" >&2
  exit 1
fi
