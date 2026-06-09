#!/usr/bin/env bash
# Integration tests for install.sh.
#
# Each test gets fresh temp dirs for every supported install target.
# Runs the real installer; asserts on the resulting symlink state and
# captured stdout/stderr.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL="$REPO_DIR/install.sh"
REAL_REPO_DIR="$REPO_DIR"
REAL_INSTALL="$INSTALL"

SKILLS_EXPECTED=()
for d in "$REPO_DIR"/skills/*/; do
  [[ -d "$d" ]] && SKILLS_EXPECTED+=("$(basename "$d")")
done
if (( ${#SKILLS_EXPECTED[@]} == 0 )); then
  echo "no skills found under $REPO_DIR/skills" >&2
  exit 1
fi

pass=0
fail=0
failures=()

# Assertions print nothing on success, a reason on failure, and always return 0
# so the calling test can accumulate multiple assertions. The per-test wrapper
# counts failures via ERR_COUNT.
ERR_COUNT=0

note_fail() {
  ERR_COUNT=$((ERR_COUNT + 1))
  echo "    $1" >&2
}

assert_symlink_to() {
  local path="$1" expected="$2"
  if [[ ! -L "$path" ]]; then
    note_fail "expected symlink at $path"
    return
  fi
  local actual
  actual="$(readlink "$path")"
  if [[ "$actual" != "$expected" ]]; then
    note_fail "expected $path -> $expected, got -> $actual"
  fi
}

assert_not_symlink() {
  local path="$1"
  if [[ -L "$path" ]]; then
    note_fail "expected $path to not be a symlink, but it is (-> $(readlink "$path"))"
  fi
}

assert_file_contents() {
  local path="$1" expected="$2"
  if [[ ! -f "$path" ]]; then
    note_fail "expected regular file at $path"
    return
  fi
  local actual
  actual="$(cat "$path")"
  if [[ "$actual" != "$expected" ]]; then
    note_fail "expected contents of $path to be '$expected', got '$actual'"
  fi
}

assert_file_exists() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    note_fail "expected regular file at $path"
  fi
}

assert_stdout_contains() {
  local needle="$1"
  if ! grep -qF -- "$needle" "$STDOUT"; then
    note_fail "expected stdout to contain: $needle"
  fi
}

assert_stderr_contains() {
  local needle="$1"
  if ! grep -qF -- "$needle" "$STDERR"; then
    note_fail "expected stderr to contain: $needle"
  fi
}

assert_stderr_lacks() {
  local needle="$1"
  if grep -qF -- "$needle" "$STDERR"; then
    note_fail "expected stderr NOT to contain: $needle"
  fi
}

assert_file_contains() {
  local path="$1" needle="$2"
  if [[ ! -f "$path" ]]; then
    note_fail "expected regular file at $path"
    return
  fi
  if ! grep -qF -- "$needle" "$path"; then
    note_fail "expected $path to contain: $needle"
  fi
}

assert_dir_exists() {
  local path="$1"
  if [[ ! -d "$path" ]]; then
    note_fail "expected directory at $path"
  fi
}

assert_json_field() {
  local path="$1" field="$2" expected="$3"
  if [[ ! -f "$path" ]]; then
    note_fail "expected JSON file at $path"
    return
  fi
  local actual
  actual="$(python3 - <<'PY' "$path" "$field"
import json, sys
path, field = sys.argv[1:]
data = json.load(open(path, encoding='utf-8'))
cur = data
for part in field.split('.'):
    cur = cur[part]
print(cur)
PY
)"
  if [[ "$actual" != "$expected" ]]; then
    note_fail "expected $field in $path to be '$expected', got '$actual'"
  fi
}

assert_json_missing() {
  local path="$1" field="$2"
  if [[ ! -f "$path" ]]; then
    note_fail "expected JSON file at $path"
    return
  fi
  local rc=0
  python3 - <<'PY' "$path" "$field" || rc=$?
import json, sys
path, field = sys.argv[1:]
try:
    data = json.load(open(path, encoding='utf-8'))
except json.JSONDecodeError:
    sys.exit(3)
except Exception:
    sys.exit(4)
cur = data
for part in field.split('.'):
    if not isinstance(cur, dict) or part not in cur:
        sys.exit(2)
    cur = cur[part]
sys.exit(0)
PY
  case "$rc" in
    0) note_fail "expected $field to be missing from $path" ;;
    2) ;; # missing as expected
    3) note_fail "invalid JSON at $path" ;;
    *) note_fail "error reading $path" ;;
  esac
}

run_installer() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local rc=0
  CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
  AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
  CODEX_SKILLS_DIR="$CODEX_SKILLS" \
  CLAUDE_HOOKS_DIR="$HOOKS" \
  BEISLID_BIN_DIR="$BIN_DIR" \
  BEISLID_STATE_DIR="$STATE" \
  BEISLID_FAKE_PI_LOG="${BEISLID_FAKE_PI_LOG:-}" \
  PATH="$TMP/bin:$PATH" \
    "$INSTALL" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

run_installer_without_path_bin() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local rc=0
  CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
  AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
  CODEX_SKILLS_DIR="$CODEX_SKILLS" \
  CLAUDE_HOOKS_DIR="$HOOKS" \
  BEISLID_BIN_DIR="$BIN_DIR" \
  BEISLID_STATE_DIR="$STATE" \
  PATH="/usr/bin:/bin" \
    "$INSTALL" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

run_installer_with_ambient_home() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local ambient_home="$1"
  shift
  local rc=0
  CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
  AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
  CODEX_SKILLS_DIR="$CODEX_SKILLS" \
  CLAUDE_HOOKS_DIR="$HOOKS" \
  BEISLID_BIN_DIR="$BIN_DIR" \
  BEISLID_STATE_DIR="$STATE" \
  BEISLID_HOME="$ambient_home" \
  PATH="$TMP/bin:$PATH" \
    "$INSTALL" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

run_installer_with_option_env() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local rc=0
  CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
  AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
  CODEX_SKILLS_DIR="$CODEX_SKILLS" \
  CLAUDE_HOOKS_DIR="$HOOKS" \
  BEISLID_BIN_DIR="$BIN_DIR" \
  BEISLID_STATE_DIR="$STATE" \
  BEISLID_FAKE_PI_LOG="${BEISLID_FAKE_PI_LOG:-}" \
  FORCE=1 \
  WITH_SECURITY_HOOKS=1 \
  WITH_PI_SHOW_ME=1 \
  PATH="$TMP/bin:$PATH" \
    "$INSTALL" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

run_cli() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local rc=0
  CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
  AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
  CODEX_SKILLS_DIR="$CODEX_SKILLS" \
  CLAUDE_HOOKS_DIR="$HOOKS" \
  BEISLID_BIN_DIR="$BIN_DIR" \
  BEISLID_STATE_DIR="$STATE" \
  BEISLID_FAKE_PI_LOG="${BEISLID_FAKE_PI_LOG:-}" \
  PATH="$TMP/bin:$PATH" \
    "$REPO_DIR/bin/beislid" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

run_cli_with_option_env() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local rc=0
  CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
  AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
  CODEX_SKILLS_DIR="$CODEX_SKILLS" \
  CLAUDE_HOOKS_DIR="$HOOKS" \
  BEISLID_BIN_DIR="$BIN_DIR" \
  BEISLID_STATE_DIR="$STATE" \
  BEISLID_FAKE_PI_LOG="${BEISLID_FAKE_PI_LOG:-}" \
  FORCE=1 \
  WITH_SECURITY_HOOKS=1 \
  WITH_PI_SHOW_ME=1 \
  PATH="$TMP/bin:$PATH" \
    "$REPO_DIR/bin/beislid" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

run_cli_with_ambient_home() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local ambient_home="$1"
  shift
  local rc=0
  CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
  AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
  CODEX_SKILLS_DIR="$CODEX_SKILLS" \
  CLAUDE_HOOKS_DIR="$HOOKS" \
  BEISLID_BIN_DIR="$BIN_DIR" \
  BEISLID_STATE_DIR="$STATE" \
  BEISLID_HOME="$ambient_home" \
  PATH="$TMP/bin:$PATH" \
    "$REPO_DIR/bin/beislid" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

run_packaged_cli() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local packaged_cli="$1"
  local ambient_home="$2"
  shift 2
  local rc=0
  if [[ -n "$ambient_home" ]]; then
    CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
    AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
    CODEX_SKILLS_DIR="$CODEX_SKILLS" \
    CLAUDE_HOOKS_DIR="$HOOKS" \
    BEISLID_BIN_DIR="$BIN_DIR" \
    BEISLID_STATE_DIR="$STATE" \
    BEISLID_HOME="$ambient_home" \
    PATH="$TMP/bin:$PATH" \
      "$packaged_cli" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  else
    CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
    AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
    CODEX_SKILLS_DIR="$CODEX_SKILLS" \
    CLAUDE_HOOKS_DIR="$HOOKS" \
    BEISLID_BIN_DIR="$BIN_DIR" \
    BEISLID_STATE_DIR="$STATE" \
    PATH="$TMP/bin:$PATH" \
      "$packaged_cli" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  fi
  return "$rc"
}

run_cli_from_dir() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local cwd="$1"
  shift
  local rc=0
  (
    cd "$cwd" || exit 99
    CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
    AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
    CODEX_SKILLS_DIR="$CODEX_SKILLS" \
    CLAUDE_HOOKS_DIR="$HOOKS" \
    BEISLID_BIN_DIR="$BIN_DIR" \
    BEISLID_STATE_DIR="$STATE" \
    BEISLID_FAKE_PI_LOG="${BEISLID_FAKE_PI_LOG:-}" \
    PATH="$TMP/bin:$PATH" \
      "$REPO_DIR/bin/beislid" "$@"
  ) >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

run_installer_without_target_env() {
  STDOUT="$TMP/stdout.log"
  STDERR="$TMP/stderr.log"
  local rc=0
  BEISLID_STATE_DIR="$STATE" \
  BEISLID_FAKE_PI_LOG="${BEISLID_FAKE_PI_LOG:-}" \
  PATH="$TMP/bin:$PATH" \
    "$INSTALL" "$@" >"$STDOUT" 2>"$STDERR" || rc=$?
  return "$rc"
}

setup() {
  TMP="$(mktemp -d)"
  REPO_DIR="$REAL_REPO_DIR"
  INSTALL="$REAL_INSTALL"
  CLAUDE_SKILLS="$TMP/claude-skills"
  AGENTS_SKILLS="$TMP/agents-skills"
  CODEX_SKILLS="$TMP/codex-skills"
  HOOKS="$TMP/hooks"
  STATE="$TMP/state"
  BIN_DIR="$TMP/bin"
  mkdir -p "$CLAUDE_SKILLS" "$AGENTS_SKILLS" "$CODEX_SKILLS" "$HOOKS" "$STATE" "$BIN_DIR"
  ERR_COUNT=0
}

teardown() {
  REPO_DIR="$REAL_REPO_DIR"
  INSTALL="$REAL_INSTALL"
  [[ -n "${TMP:-}" ]] && rm -rf "$TMP"
}

fixture_git() {
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 git "$@"
}

setup_update_git_fixture() {
  UPDATE_ORIGIN="$TMP/update-origin"
  UPDATE_INSTALL="$TMP/update-install"
  mkdir -p "$UPDATE_ORIGIN"
  tar --exclude=.git --exclude=.pytest_cache -C "$REAL_REPO_DIR" -cf - . | tar -C "$UPDATE_ORIGIN" -xf -
  fixture_git -C "$UPDATE_ORIGIN" init -q
  fixture_git -C "$UPDATE_ORIGIN" config user.email beislid-test@example.com
  fixture_git -C "$UPDATE_ORIGIN" config user.name "Beislið Test"
  fixture_git -C "$UPDATE_ORIGIN" add .
  fixture_git -C "$UPDATE_ORIGIN" commit -q -m initial
  fixture_git clone -q "$UPDATE_ORIGIN" "$UPDATE_INSTALL"
  fixture_git -C "$UPDATE_INSTALL" config user.email beislid-test@example.com
  fixture_git -C "$UPDATE_INSTALL" config user.name "Beislið Test"
  REPO_DIR="$UPDATE_INSTALL"
  INSTALL="$UPDATE_INSTALL/install.sh"
}

commit_update_fixture_change() {
  local marker="$1"
  printf '\n%s\n' "$marker" >>"$UPDATE_ORIGIN/skills/verify/SKILL.md"
  fixture_git -C "$UPDATE_ORIGIN" add skills/verify/SKILL.md
  fixture_git -C "$UPDATE_ORIGIN" commit -q -m "$marker"
}

run_test() {
  local name="$1"
  local fn="$2"
  echo "-- $name"
  setup
  if ! "$fn"; then
    ERR_COUNT=$((ERR_COUNT + 1))
    note_fail "test function returned non-zero"
  fi
  if (( ERR_COUNT > 0 )); then
    fail=$((fail + 1))
    failures+=("$name")
    echo "   FAIL ($ERR_COUNT assertion(s))" >&2
  else
    pass=$((pass + 1))
    echo "   pass"
  fi
  teardown
}

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

test_fresh_install() {
  run_installer --with-security-hooks
  for skill in "${SKILLS_EXPECTED[@]}"; do
    assert_symlink_to "$CLAUDE_SKILLS/$skill" "$REPO_DIR/skills/$skill"
    assert_symlink_to "$AGENTS_SKILLS/$skill" "$REPO_DIR/skills/$skill"
    assert_symlink_to "$CODEX_SKILLS/$skill" "$REPO_DIR/skills/$skill"
  done
  assert_symlink_to "$HOOKS/credential_guard.py" "$REPO_DIR/hooks/credential_guard.py"
  assert_symlink_to "$HOOKS/credential_guard.json" "$REPO_DIR/hooks/credential_guard.json"
}

test_idempotent_rerun() {
  run_installer --with-security-hooks
  run_installer --with-security-hooks
  assert_stdout_contains "ok:   verify (claude) (already linked)"
  assert_stdout_contains "ok:   hook credential_guard.py (already linked)"
  assert_stdout_contains "ok:   hook credential_guard.json (already linked)"
}

test_dangling_symlink_autorepair() {
  # Stale symlink from a previous install at a different repo location.
  ln -s /nonexistent/old/path/skills/verify "$CLAUDE_SKILLS/verify"
  ln -s /nonexistent/old/path/hooks/credential_guard.py "$HOOKS/credential_guard.py"
  run_installer --with-security-hooks
  assert_symlink_to "$CLAUDE_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$HOOKS/credential_guard.py" "$REPO_DIR/hooks/credential_guard.py"
  assert_stdout_contains "fix:  verify (claude) (repaired dangling link; was pointing at"
  assert_stdout_contains "fix:  hook credential_guard.py (repaired dangling link; was pointing at"
  assert_stderr_lacks "failed to create symbolic link"
}

test_wrong_target_skipped_without_force() {
  # A live symlink pointing at a different, valid skill dir.
  local other="$TMP/other-beislid/skills/verify"
  mkdir -p "$other"
  ln -s "$other" "$CLAUDE_SKILLS/verify"
  run_installer
  assert_symlink_to "$CLAUDE_SKILLS/verify" "$other"
  assert_stderr_contains "symlinked elsewhere"
  assert_stderr_contains "--force"
}

test_wrong_target_repointed_with_force() {
  local other="$TMP/other-beislid/skills/verify"
  mkdir -p "$other"
  ln -s "$other" "$CLAUDE_SKILLS/verify"
  run_installer --force
  assert_symlink_to "$CLAUDE_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_stdout_contains "fix:  verify (claude) (repointed from"
}

test_regular_file_never_clobbered() {
  mkdir -p "$CLAUDE_SKILLS/verify"
  printf 'user content\n' >"$CLAUDE_SKILLS/verify/SKILL.md"
  run_installer --force
  assert_not_symlink "$CLAUDE_SKILLS/verify"
  assert_file_contents "$CLAUDE_SKILLS/verify/SKILL.md" "user content"
  assert_stderr_contains "not a symlink"
}

test_legacy_skill_symlinks_are_removed() {
  local old_beislid="$TMP/beislid-pre-v0.2"
  local foreign_ship_it="$TMP/foreign-tools/claude-skills/ship-it"
  local foreign_heard_chef="$TMP/foreign-tools/claude-skills/heard-chef"
  mkdir -p "$old_beislid/skills/ship-it" "$old_beislid/skills/heard-chef" "$foreign_ship_it" "$foreign_heard_chef"
  printf '#!/usr/bin/env bash\n' >"$old_beislid/install.sh"
  printf '{"name":"beislid"}\n' >"$old_beislid/package.json"
  ln -s "$REPO_DIR/skills/check-done" "$CLAUDE_SKILLS/check-done"
  ln -s "$REPO_DIR/skills/start-ticket" "$AGENTS_SKILLS/start-ticket"
  ln -s "$old_beislid/skills/heard-chef" "$CLAUDE_SKILLS/heard-chef"
  ln -s "$foreign_ship_it" "$AGENTS_SKILLS/ship-it"
  ln -s "$foreign_heard_chef" "$AGENTS_SKILLS/heard-chef"
  ln -s "$old_beislid/skills/ship-it" "$CODEX_SKILLS/ship-it"
  run_installer
  if [[ -e "$CLAUDE_SKILLS/check-done" || -L "$CLAUDE_SKILLS/check-done" ]]; then
    note_fail "expected legacy check-done symlink to be removed"
  fi
  if [[ -e "$AGENTS_SKILLS/start-ticket" || -L "$AGENTS_SKILLS/start-ticket" ]]; then
    note_fail "expected legacy start-ticket symlink to be removed"
  fi
  if [[ -e "$CODEX_SKILLS/ship-it" || -L "$CODEX_SKILLS/ship-it" ]]; then
    note_fail "expected legacy ship-it symlink to be removed"
  fi
  if [[ -e "$CLAUDE_SKILLS/heard-chef" || -L "$CLAUDE_SKILLS/heard-chef" ]]; then
    note_fail "expected legacy heard-chef symlink to be removed"
  fi
  assert_symlink_to "$AGENTS_SKILLS/ship-it" "$foreign_ship_it"
  assert_symlink_to "$AGENTS_SKILLS/heard-chef" "$foreign_heard_chef"
  assert_symlink_to "$CLAUDE_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$AGENTS_SKILLS/kickoff" "$REPO_DIR/skills/kickoff"
}

test_install_writes_manifest() {
  run_installer --with-security-hooks
  local manifest="$STATE/install.json"
  local expected_version
  expected_version="$(python3 - <<'PY' "$REPO_DIR/.claude-plugin/plugin.json"
import json, sys
print(json.load(open(sys.argv[1], encoding='utf-8'))['version'])
PY
)"
  assert_json_field "$manifest" repo "$REPO_DIR"
  assert_json_field "$manifest" version "$expected_version"
  assert_json_field "$manifest" skill_dirs.claude "$CLAUDE_SKILLS"
  assert_json_field "$manifest" skill_dirs.agents "$AGENTS_SKILLS"
  assert_json_field "$manifest" skill_dirs.codex "$CODEX_SKILLS"
  assert_json_field "$manifest" hooks_dir "$HOOKS"
  assert_json_field "$manifest" security_hooks "True"
  assert_json_field "$manifest" pi_show_me "False"
  assert_json_field "$manifest" bin_dir "$BIN_DIR"
  assert_json_field "$manifest" cli_path "$BIN_DIR/beislid"
  assert_stdout_contains "manifest: $manifest"
}

test_cli_linked_by_default() {
  run_installer
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  assert_stdout_contains "CLI:"
  assert_stdout_contains "link: beislid CLI"
}

test_install_sh_ignores_ambient_beislid_home() {
  local other="$TMP/other-beislid"
  mkdir -p "$other/bin" "$other/skills/verify" "$other/scripts"
  printf '#!/usr/bin/env bash\n' >"$other/bin/beislid"
  run_installer_with_ambient_home "$other"
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  assert_symlink_to "$CLAUDE_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_json_field "$STATE/install.json" repo "$REPO_DIR"
}

test_install_sh_ignores_ambient_option_flags() {
  fake_pi
  local other="$TMP/other-beislid-cli"
  printf '#!/usr/bin/env bash\n' >"$other"
  ln -s "$other" "$BIN_DIR/beislid"

  BEISLID_FAKE_PI_LOG="$TMP/pi.log" run_installer_with_option_env

  assert_symlink_to "$BIN_DIR/beislid" "$other"
  assert_stderr_contains "beislid CLI symlinked elsewhere"
  if [[ -e "$HOOKS/credential_guard.py" || -e "$HOOKS/credential_guard.json" ]]; then
    note_fail "expected ambient WITH_SECURITY_HOOKS not to install hooks"
  fi
  if [[ -e "$TMP/pi.log" ]]; then
    note_fail "expected ambient WITH_PI_SHOW_ME not to call pi"
  fi
  assert_json_field "$STATE/install.json" security_hooks "False"
  assert_json_field "$STATE/install.json" pi_show_me "False"
}

test_cli_bin_dir_override() {
  BIN_DIR="$TMP/custom-bin"
  run_installer
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  assert_json_field "$STATE/install.json" bin_dir "$BIN_DIR"
  assert_json_field "$STATE/install.json" cli_path "$BIN_DIR/beislid"
}

test_cli_path_warning() {
  BIN_DIR="$TMP/not-on-path"
  run_installer_without_path_bin
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  assert_stderr_contains "warn: $BIN_DIR is not on PATH"
}

test_cli_regular_file_never_clobbered() {
  printf 'user cli\n' >"$BIN_DIR/beislid"
  run_installer --force
  assert_not_symlink "$BIN_DIR/beislid"
  assert_file_contents "$BIN_DIR/beislid" "user cli"
  assert_stderr_contains "beislid CLI exists at $BIN_DIR/beislid (not a symlink), skipping"
  assert_json_missing "$STATE/install.json" bin_dir
  assert_json_missing "$STATE/install.json" cli_path
}

test_cli_foreign_symlink_safety() {
  local other="$TMP/other-beislid-cli"
  printf '#!/usr/bin/env bash\n' >"$other"
  ln -s "$other" "$BIN_DIR/beislid"

  run_installer
  assert_symlink_to "$BIN_DIR/beislid" "$other"
  assert_stderr_contains "beislid CLI symlinked elsewhere"

  run_installer --force
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  assert_stdout_contains "fix:  beislid CLI (repointed from"
}

test_cli_dangling_symlink_repaired() {
  ln -s /nonexistent/old/beislid "$BIN_DIR/beislid"
  run_installer
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  assert_stdout_contains "fix:  beislid CLI (repaired dangling link; was pointing at"
}

write_pre_v0_2_manifest() {
  local old_repo="$1"
  python3 - <<'PY' "$STATE/install.json" "$old_repo" "$CLAUDE_SKILLS" "$AGENTS_SKILLS" "$CODEX_SKILLS" "$HOOKS" "$BIN_DIR"
import json, os, sys
manifest, repo, claude, agents, codex, hooks, bin_dir = sys.argv[1:]
os.makedirs(os.path.dirname(manifest), exist_ok=True)
data = {
    "installed_at": "2026-05-01T00:00:00Z",
    "repo": repo,
    "version": "0.1.13",
    "git_commit": "pre-v0.2",
    "skill_dirs": {"claude": claude, "agents": agents, "codex": codex},
    "hooks_dir": hooks,
    "security_hooks": True,
    "pi_show_me": False,
    "bin_dir": bin_dir,
    "cli_path": os.path.join(bin_dir, "beislid"),
}
with open(manifest, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
}

test_migrate_v0_2_repoints_previous_manifest_install() {
  local old_repo="$TMP/old-beislid"
  local foreign="$TMP/foreign-skills/spec"
  mkdir -p \
    "$old_repo/skills/verify" \
    "$old_repo/skills/ship-it" \
    "$old_repo/skills/check-done" \
    "$old_repo/hooks" \
    "$old_repo/bin" \
    "$foreign" \
    "$CODEX_SKILLS/debug"
  printf 'old verify\n' >"$old_repo/skills/verify/SKILL.md"
  printf 'old ship-it\n' >"$old_repo/skills/ship-it/SKILL.md"
  printf 'old check-done\n' >"$old_repo/skills/check-done/SKILL.md"
  printf 'old hook\n' >"$old_repo/hooks/credential_guard.py"
  printf '#!/usr/bin/env bash\n' >"$old_repo/bin/beislid"
  printf 'foreign spec\n' >"$foreign/SKILL.md"
  printf 'user debug\n' >"$CODEX_SKILLS/debug/SKILL.md"
  ln -s "$old_repo/skills/verify" "$CLAUDE_SKILLS/verify"
  ln -s "$old_repo/skills/check-done" "$AGENTS_SKILLS/check-done"
  ln -s "$old_repo/skills/ship-it" "$CODEX_SKILLS/ship-it"
  ln -s "$foreign" "$AGENTS_SKILLS/spec"
  ln -s "$old_repo/hooks/credential_guard.py" "$HOOKS/credential_guard.py"
  ln -s "$old_repo/bin/beislid" "$BIN_DIR/beislid"
  write_pre_v0_2_manifest "$old_repo"

  run_installer --migrate-v0.2

  assert_stdout_contains "Migration v0.2:"
  assert_stdout_contains "previous_repo: $old_repo"
  assert_stdout_contains "cleanup: removed"
  assert_symlink_to "$CLAUDE_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$CODEX_SKILLS/ready-for-review" "$REPO_DIR/skills/ready-for-review"
  if [[ -e "$CODEX_SKILLS/ship-it" || -L "$CODEX_SKILLS/ship-it" ]]; then
    note_fail "expected legacy ship-it link into old repo to be removed"
  fi
  assert_symlink_to "$HOOKS/credential_guard.py" "$REPO_DIR/hooks/credential_guard.py"
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  if [[ -e "$AGENTS_SKILLS/check-done" || -L "$AGENTS_SKILLS/check-done" ]]; then
    note_fail "expected legacy check-done link into old repo to be removed"
  fi
  assert_symlink_to "$AGENTS_SKILLS/spec" "$foreign"
  assert_file_contents "$CODEX_SKILLS/debug/SKILL.md" "user debug"
  assert_json_field "$STATE/install.json" repo "$REPO_DIR"
  assert_json_field "$STATE/install.json" security_hooks "True"
}

test_cli_migrate_v0_2_delegates_to_shared_migration() {
  local old_repo="$TMP/old-beislid-cli"
  mkdir -p "$old_repo/skills/verify" "$old_repo/bin"
  printf 'old verify\n' >"$old_repo/skills/verify/SKILL.md"
  printf '#!/usr/bin/env bash\n' >"$old_repo/bin/beislid"
  ln -s "$old_repo/skills/verify" "$AGENTS_SKILLS/verify"
  ln -s "$old_repo/bin/beislid" "$BIN_DIR/beislid"
  write_pre_v0_2_manifest "$old_repo"

  run_cli migrate v0.2

  assert_stdout_contains "Migration v0.2:"
  assert_symlink_to "$AGENTS_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
}

fake_pi() {
  cat >"$TMP/bin/pi" <<'SH'
#!/usr/bin/env bash
echo "$@" >>"$BEISLID_FAKE_PI_LOG"
SH
  chmod +x "$TMP/bin/pi"
}


test_pi_show_me_is_opt_in() {
  fake_pi
  BEISLID_FAKE_PI_LOG="$TMP/pi.log" run_installer
  if [[ -e "$TMP/pi.log" ]]; then
    note_fail "expected pi not to be called without --with-pi-show-me"
  fi
  assert_json_field "$STATE/install.json" pi_show_me "False"
}


test_pi_show_me_installs_package_when_requested() {
  fake_pi
  BEISLID_FAKE_PI_LOG="$TMP/pi.log" run_installer --with-pi-show-me
  assert_file_contents "$TMP/pi.log" "install $REPO_DIR"
  assert_json_field "$STATE/install.json" pi_show_me "True"
  assert_stdout_contains "Pi show-me extension:"
  assert_stdout_contains "ok:   pi package installed for show-me extension"
}

test_status_after_install() {
  run_installer
  run_installer --status
  assert_stdout_contains "beislid status"
  assert_stdout_contains "manifest: $STATE/install.json"
  assert_stdout_contains "✓ verify"
  assert_stdout_contains "current_commit:"
  assert_stdout_contains "cli: $BIN_DIR/beislid"
  assert_stdout_contains "✓ beislid"
}

test_status_reports_broken_cli_link() {
  run_installer
  rm "$BIN_DIR/beislid"
  if run_installer --status; then
    note_fail "expected status to fail when CLI link is missing"
  fi
  assert_stdout_contains "cli: $BIN_DIR/beislid"
  assert_stdout_contains "✗ beislid"
}

test_status_reports_enabled_hook_links() {
  run_installer --with-security-hooks
  rm "$HOOKS/credential_guard.json"
  if run_installer --status; then
    note_fail "expected status to fail when enabled hook link is missing"
  fi
  assert_stdout_contains "hooks: $HOOKS"
  assert_stdout_contains "✓ credential_guard.py"
  assert_stdout_contains "✗ credential_guard.json"
}

test_status_handles_malformed_manifest() {
  run_installer
  printf '{not json\n' >"$STATE/install.json"
  run_installer --status
  assert_stdout_contains "manifest: unreadable ($STATE/install.json)"
  assert_stdout_contains "✓ verify"
  assert_stdout_contains "✓ beislid"
}

test_cli_help() {
  run_cli help
  assert_stdout_contains "beislid install user"
  assert_stdout_contains "beislid status"
  assert_stdout_contains "beislid update"
}

test_cli_ignores_ambient_beislid_home() {
  run_cli_with_ambient_home /nonexistent/beislid help
  assert_stdout_contains "beislid install user"
  assert_stdout_contains "beislid status"
}

test_packaged_cli_uses_beislid_home_when_layout_missing() {
  local package_root="$TMP/package-root"
  mkdir -p "$package_root/bin"
  cp "$REPO_DIR/bin/beislid" "$package_root/bin/beislid"
  chmod +x "$package_root/bin/beislid"

  run_packaged_cli "$package_root/bin/beislid" "$REPO_DIR" help
  assert_stdout_contains "beislid install user"
  assert_stdout_contains "beislid install project"
}

test_packaged_cli_uses_beislid_home_when_run_ledger_missing() {
  local package_root="$TMP/package-missing-run-ledger"
  mkdir -p "$package_root/bin" "$package_root/scripts" "$package_root/skills"
  cp "$REPO_DIR/bin/beislid" "$package_root/bin/beislid"
  cp "$REPO_DIR/scripts/install_lib.sh" "$package_root/scripts/install_lib.sh"
  cp "$REPO_DIR/install.sh" "$package_root/install.sh"
  chmod +x "$package_root/bin/beislid"

  run_packaged_cli "$package_root/bin/beislid" "$REPO_DIR" run-ledger init --skill kickoff --flow kickoff --run-id packaged-fallback-test
  assert_stdout_contains '"run_id": "packaged-fallback-test"'
}

test_packaged_cli_reports_incomplete_layout() {
  local package_root="$TMP/broken-package"
  mkdir -p "$package_root/bin"
  cp "$REPO_DIR/bin/beislid" "$package_root/bin/beislid"
  chmod +x "$package_root/bin/beislid"

  if run_packaged_cli "$package_root/bin/beislid" "" help; then
    note_fail "expected packaged CLI with missing runtime layout to fail"
  fi
  assert_stderr_contains "Beislið runtime layout is incomplete"
  assert_stderr_contains "missing: scripts/install_lib.sh"
  assert_stderr_contains "Set BEISLID_HOME"
}

test_packaged_cli_reports_invalid_beislid_home_as_layout_error() {
  local package_root="$TMP/package-invalid-home"
  mkdir -p "$package_root/bin"
  cp "$REPO_DIR/bin/beislid" "$package_root/bin/beislid"
  chmod +x "$package_root/bin/beislid"

  if run_packaged_cli "$package_root/bin/beislid" "$TMP/missing-beislid-home" help; then
    note_fail "expected packaged CLI with invalid BEISLID_HOME to fail"
  fi
  assert_stderr_contains "Beislið runtime layout is incomplete at $TMP/missing-beislid-home"
  assert_stderr_contains "missing: scripts/install_lib.sh"
  assert_stderr_contains "Set BEISLID_HOME"
}

test_packaged_cli_supports_homebrew_symlink_layout() {
  local cellar="$TMP/homebrew-cellar"
  local libexec="$cellar/libexec"
  mkdir -p "$cellar/bin" "$libexec/bin" "$libexec/scripts" "$libexec/skills"
  cp "$REPO_DIR/bin/beislid" "$libexec/bin/beislid"
  cp "$REPO_DIR/scripts/install_lib.sh" "$libexec/scripts/install_lib.sh"
  cp "$REPO_DIR/scripts/run_ledger.py" "$libexec/scripts/run_ledger.py"
  cp "$REPO_DIR/scripts/action_policy.py" "$libexec/scripts/action_policy.py"
  cp "$REPO_DIR/install.sh" "$libexec/install.sh"
  chmod +x "$libexec/bin/beislid"
  ln -s "$libexec/bin/beislid" "$cellar/bin/beislid"

  run_packaged_cli "$cellar/bin/beislid" "" help
  assert_stdout_contains "beislid install user"
  assert_stdout_contains "beislid install project"
}

test_homebrew_formula_draft_installs_runtime_subset() {
  local formula="$REPO_DIR/packaging/homebrew/beislid.rb"
  assert_file_contains "$formula" "class Beislid < Formula"
  assert_file_contains "$formula" "bin/beislid"
  assert_file_contains "$formula" "skills"
  assert_file_contains "$formula" "scripts/install_lib.sh"
  assert_file_contains "$formula" "scripts/run_ledger.py"
  assert_file_contains "$formula" "scripts/action_policy.py"
  assert_file_contains "$formula" "install.sh"
  assert_file_contains "$formula" "Full Homebrew support"
}

test_cli_install_user() {
  run_cli install user
  assert_symlink_to "$CLAUDE_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  assert_stdout_contains "==> Beislið install ($REPO_DIR)"
}

test_cli_ignores_ambient_option_flags() {
  fake_pi
  local other="$TMP/other-beislid-cli"
  printf '#!/usr/bin/env bash\n' >"$other"
  ln -s "$other" "$BIN_DIR/beislid"

  BEISLID_FAKE_PI_LOG="$TMP/pi.log" run_cli_with_option_env install user

  assert_symlink_to "$BIN_DIR/beislid" "$other"
  assert_stderr_contains "beislid CLI symlinked elsewhere"
  if [[ -e "$HOOKS/credential_guard.py" || -e "$HOOKS/credential_guard.json" ]]; then
    note_fail "expected ambient WITH_SECURITY_HOOKS not to install hooks via CLI"
  fi
  if [[ -e "$TMP/pi.log" ]]; then
    note_fail "expected ambient WITH_PI_SHOW_ME not to call pi via CLI"
  fi
  assert_json_field "$STATE/install.json" security_hooks "False"
  assert_json_field "$STATE/install.json" pi_show_me "False"
}

test_cli_status() {
  run_installer
  run_cli status
  assert_stdout_contains "beislid status"
  assert_stdout_contains "manifest: $STATE/install.json"
  assert_stdout_contains "cli_path: $BIN_DIR/beislid"
  assert_stdout_contains "✓ verify"
}

test_workflow_signal_noops_when_unconfigured() {
  local project="$TMP/workflow-signal-unconfigured"
  mkdir -p "$project"
  cat >"$TMP/bin/tmux-glance" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$BEISLID_FAKE_PI_LOG"
SH
  chmod +x "$TMP/bin/tmux-glance"

  BEISLID_FAKE_PI_LOG="$TMP/tmux-glance.log" TMUX=fake run_cli_from_dir "$project" workflow-signal emit waiting --skill poke-holes
  if [[ -e "$TMP/tmux-glance.log" ]]; then
    note_fail "expected unconfigured workflow-signal emit not to invoke tmux-glance"
  fi

  run_cli_from_dir "$project" workflow-signal status
  assert_stdout_contains "workflow_signals: not configured"
}

test_workflow_signal_tmux_glance_requires_tmux() {
  local project="$TMP/workflow-signal-no-tmux"
  mkdir -p "$project/.beislid"
  cat >"$project/.beislid/workflow.md" <<'MD'
<!-- beislid-workflow: v1 -->

## Workflow signals

```beislid:workflow_signals
mode: auto
sinks:
  - type: tmux-glance
skills:
  poke-holes: auto
```
MD
  cat >"$TMP/bin/tmux-glance" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$BEISLID_FAKE_PI_LOG"
SH
  chmod +x "$TMP/bin/tmux-glance"

  BEISLID_FAKE_PI_LOG="$TMP/tmux-glance.log" TMUX='' run_cli_from_dir "$project" workflow-signal emit waiting --skill poke-holes
  if [[ -e "$TMP/tmux-glance.log" ]]; then
    note_fail "expected workflow-signal emit outside tmux not to invoke tmux-glance"
  fi
}

test_workflow_signal_tmux_glance_invokes_sink() {
  local project="$TMP/workflow-signal-tmux"
  mkdir -p "$project/.beislid"
  cat >"$project/.beislid/workflow.md" <<'MD'
<!-- beislid-workflow: v1 -->

## Workflow signals

```beislid:workflow_signals
mode: auto
sinks:
  - type: tmux-glance
skills:
  poke-holes: auto
```
MD
  cat >"$TMP/bin/tmux-glance" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$BEISLID_FAKE_PI_LOG"
SH
  chmod +x "$TMP/bin/tmux-glance"

  BEISLID_FAKE_PI_LOG="$TMP/tmux-glance.log" TMUX=fake run_cli_from_dir "$project" workflow-signal emit waiting --skill poke-holes --phase question
  assert_file_contains "$TMP/tmux-glance.log" "waiting"

  run_cli_from_dir "$project" workflow-signal status --skill poke-holes
  assert_stdout_contains "mode: auto"
  assert_stdout_contains "skill_mode: auto"
  assert_stdout_contains "sink: tmux-glance"
}

test_workflow_signal_skill_override_can_disable() {
  local project="$TMP/workflow-signal-skill-off"
  mkdir -p "$project/.beislid"
  cat >"$project/.beislid/workflow.md" <<'MD'
<!-- beislid-workflow: v1 -->

## Workflow signals

```beislid:workflow_signals
mode: auto
sinks:
  - type: tmux-glance
skills:
  poke-holes: off
```
MD
  cat >"$TMP/bin/tmux-glance" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$BEISLID_FAKE_PI_LOG"
SH
  chmod +x "$TMP/bin/tmux-glance"

  BEISLID_FAKE_PI_LOG="$TMP/tmux-glance.log" TMUX=fake run_cli_from_dir "$project" workflow-signal emit waiting --skill poke-holes
  if [[ -e "$TMP/tmux-glance.log" ]]; then
    note_fail "expected skill-level off to suppress workflow-signal sink"
  fi
}

test_workflow_signal_invalid_modes_noop() {
  local project="$TMP/workflow-signal-invalid-mode"
  mkdir -p "$project/.beislid"
  cat >"$project/.beislid/workflow.md" <<'MD'
<!-- beislid-workflow: v1 -->

## Workflow signals

```beislid:workflow_signals
mode: prompt
sinks:
  - type: tmux-glance
skills:
  ready-for-review: disabled
```
MD
  cat >"$TMP/bin/tmux-glance" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$BEISLID_FAKE_PI_LOG"
SH
  chmod +x "$TMP/bin/tmux-glance"

  BEISLID_FAKE_PI_LOG="$TMP/tmux-glance.log" TMUX=fake run_cli_from_dir "$project" workflow-signal emit waiting --skill ready-for-review
  if [[ -e "$TMP/tmux-glance.log" ]]; then
    note_fail "expected invalid workflow-signal modes not to invoke tmux-glance"
  fi
}

test_cli_plugin_enable_lavish_writes_state() {
  run_cli plugin enable lavish
  assert_stdout_contains "Lavish plugin enabled"
  assert_stdout_contains "default command is 'npx -y lavish-axi'"
  assert_file_exists "$STATE/plugins/lavish.json"
  assert_json_field "$STATE/plugins/lavish.json" schema 1
  assert_json_field "$STATE/plugins/lavish.json" name lavish
  assert_json_field "$STATE/plugins/lavish.json" provider lavish-axi
  assert_json_field "$STATE/plugins/lavish.json" enabled True
  assert_json_field "$STATE/plugins/lavish.json" command "npx -y lavish-axi"
  assert_json_field "$STATE/plugins/lavish.json" artifact_root ".lavish"
  local mode
  mode="$(python3 - <<'PY' "$STATE/plugins/lavish.json"
import os, stat, sys
print(oct(stat.S_IMODE(os.stat(sys.argv[1]).st_mode)))
PY
)"
  if [[ "$mode" != "0o600" ]]; then
    note_fail "expected Lavish plugin state mode 0o600, got $mode"
  fi
}

test_cli_plugin_status_lavish_reports_light_probe() {
  cat >"$TMP/bin/npx" <<'SH'
#!/usr/bin/env bash
exit 0
SH
  chmod +x "$TMP/bin/npx"
  run_cli plugin enable lavish
  run_cli plugin status lavish
  assert_stdout_contains "beislid plugin status lavish"
  assert_stdout_contains "enabled: True"
  assert_stdout_contains "command: npx -y lavish-axi"
  assert_stdout_contains "artifact_root: .lavish"
  assert_stdout_contains "light_probe: ok (npx)"
}

test_cli_plugin_disable_lavish_preserves_state() {
  run_cli plugin enable lavish --command lavish-axi --artifact-root .custom-lavish
  run_cli plugin disable lavish
  assert_stdout_contains "Lavish plugin disabled"
  assert_json_field "$STATE/plugins/lavish.json" enabled False
  assert_json_field "$STATE/plugins/lavish.json" command lavish-axi
  assert_json_field "$STATE/plugins/lavish.json" artifact_root ".custom-lavish"
}

test_cli_plugin_status_lavish_deep_check() {
  cat >"$TMP/bin/npx" <<'SH'
#!/usr/bin/env bash
printf 'fake lavish help\n'
printf '%s\n' "$@" >"$BEISLID_FAKE_PI_LOG"
exit 0
SH
  chmod +x "$TMP/bin/npx"
  BEISLID_FAKE_PI_LOG="$TMP/deep-check.log" run_cli plugin enable lavish
  BEISLID_FAKE_PI_LOG="$TMP/deep-check.log" run_cli plugin status lavish --check
  assert_stdout_contains "deep_check: ok"
  assert_file_contains "$TMP/deep-check.log" "-y"
  assert_file_contains "$TMP/deep-check.log" "lavish-axi"
  assert_file_contains "$TMP/deep-check.log" "--help"
}

test_cli_plugin_errors_are_clear() {
  if run_cli plugin enable nope; then
    note_fail "expected unknown plugin enable to fail"
  fi
  assert_stderr_contains "Unknown plugin: nope"

  if run_cli plugin status lavish --bogus; then
    note_fail "expected unknown plugin status flag to fail"
  fi
  assert_stderr_contains "Unknown plugin status flag: --bogus"
}

test_cli_legacy_flag_guidance() {
  if run_cli --status; then
    note_fail "expected beislid --status to exit non-zero"
  fi
  assert_stderr_contains "Use: beislid status"

  if run_cli --update; then
    note_fail "expected beislid --update to exit non-zero"
  fi
  assert_stderr_contains "Use: beislid update"

  if run_cli --project; then
    note_fail "expected beislid --project to exit non-zero"
  fi
  assert_stderr_contains "beislid install project"
}

test_cli_unknown_command() {
  if run_cli frobnicate; then
    note_fail "expected unknown command to exit non-zero"
  fi
  assert_stderr_contains "Unknown command: frobnicate"
  assert_stderr_contains "Beislið CLI"
}

test_cli_project_install_explicit_path() {
  local project="$TMP/project-explicit"
  mkdir -p "$project"
  run_cli install project "$project"

  assert_dir_exists "$project/.agents/skills"
  assert_dir_exists "$project/.claude/skills"
  assert_dir_exists "$project/.codex/skills"
  for skill in "${SKILLS_EXPECTED[@]}"; do
    assert_symlink_to "$project/.agents/skills/$skill" "$REPO_DIR/skills/$skill"
    assert_symlink_to "$project/.claude/skills/$skill" "$REPO_DIR/skills/$skill"
    assert_symlink_to "$project/.codex/skills/$skill" "$REPO_DIR/skills/$skill"
  done
  local manifest="$project/.beislid/project-install.json"
  local expected_links=$(( ${#SKILLS_EXPECTED[@]} * 3 ))
  assert_json_field "$manifest" source_path "$REPO_DIR"
  assert_json_field "$manifest" project_path "$project"
  assert_json_field "$manifest" mode symlink
  assert_json_field "$manifest" targets.agents "$project/.agents/skills"
  assert_json_field "$manifest" targets.claude "$project/.claude/skills"
  assert_json_field "$manifest" targets.codex "$project/.codex/skills"
  assert_json_field "$manifest" counts.installed_links "$expected_links"
  assert_json_field "$manifest" counts.skipped_links 0
  assert_stdout_contains "==> Beislið project install ($project)"
  assert_stderr_contains "workflow.md not found"
}

test_cli_project_install_uses_git_root_by_default() {
  local project="$TMP/project-git"
  mkdir -p "$project/sub/dir"
  fixture_git -C "$project" init -q

  run_cli_from_dir "$project/sub/dir" install project

  assert_symlink_to "$project/.agents/skills/verify" "$REPO_DIR/skills/verify"
  if [[ -e "$project/sub/dir/.agents/skills/verify" || -L "$project/sub/dir/.agents/skills/verify" ]]; then
    note_fail "expected implicit install to target git root, not cwd subdir"
  fi
  local expected_root
  expected_root="$(git -C "$project" rev-parse --show-toplevel)"
  assert_json_field "$expected_root/.beislid/project-install.json" project_path "$expected_root"
}

test_cli_project_install_explicit_path_inside_repo_is_exact() {
  local project="$TMP/project-parent"
  local nested="$project/nested/exact-target"
  mkdir -p "$nested"
  fixture_git -C "$project" init -q

  run_cli install project "$nested"

  assert_symlink_to "$nested/.agents/skills/verify" "$REPO_DIR/skills/verify"
  if [[ -e "$project/.agents/skills/verify" || -L "$project/.agents/skills/verify" ]]; then
    note_fail "expected explicit target inside repo to be used exactly, not promoted to git root"
  fi
  assert_json_field "$nested/.beislid/project-install.json" project_path "$nested"
}

test_cli_project_install_uses_cwd_without_git_root() {
  local project="$TMP/project-nongit"
  mkdir -p "$project"

  run_cli_from_dir "$project" install project

  assert_symlink_to "$project/.codex/skills/verify" "$REPO_DIR/skills/verify"
  assert_stderr_contains "not inside a git repo; using current directory"
  assert_json_field "$project/.beislid/project-install.json" project_path "$project"
}

test_install_sh_project_compat_explicit_path() {
  local project="$TMP/project-compat"
  mkdir -p "$project"

  run_installer --project "$project"

  assert_symlink_to "$project/.claude/skills/verify" "$REPO_DIR/skills/verify"
  assert_json_field "$project/.beislid/project-install.json" mode symlink
  if [[ -e "$STATE/install.json" ]]; then
    note_fail "expected project install compatibility path not to write user install manifest"
  fi
}

test_cli_project_copy_install_explicit_path() {
  local project="$TMP/project-copy"
  mkdir -p "$project"

  run_cli install project "$project" --copy

  local expected_copies=$(( ${#SKILLS_EXPECTED[@]} * 3 ))
  for skill in "${SKILLS_EXPECTED[@]}"; do
    assert_dir_exists "$project/.agents/skills/$skill"
    assert_dir_exists "$project/.claude/skills/$skill"
    assert_dir_exists "$project/.codex/skills/$skill"
    assert_not_symlink "$project/.agents/skills/$skill"
    assert_file_exists "$project/.agents/skills/$skill/SKILL.md"
    assert_json_field "$project/.agents/skills/$skill/.beislid-owner.json" owner beislid
    assert_json_field "$project/.agents/skills/$skill/.beislid-owner.json" mode copy
    assert_json_field "$project/.agents/skills/$skill/.beislid-owner.json" skill "$skill"
  done
  local manifest="$project/.beislid/project-install.json"
  assert_json_field "$manifest" source_path "$REPO_DIR"
  assert_json_field "$manifest" project_path "$project"
  assert_json_field "$manifest" mode copy
  assert_json_field "$manifest" counts.installed_copies "$expected_copies"
  assert_json_field "$manifest" counts.refreshed_copies 0
  assert_json_field "$manifest" counts.skipped_copies 0
  assert_stdout_contains "mode: copy"
  assert_stdout_contains "# BEGIN Beislið project install"
  if [[ -e "$project/.gitignore" ]]; then
    note_fail "expected default project install not to write .gitignore"
  fi
}

test_install_sh_project_copy_compat_explicit_path() {
  local project="$TMP/project-copy-compat"
  mkdir -p "$project"

  run_installer --project "$project" --copy

  assert_dir_exists "$project/.claude/skills/verify"
  assert_not_symlink "$project/.claude/skills/verify"
  assert_json_field "$project/.beislid/project-install.json" mode copy
}

test_project_copy_never_clobbers_unmarked_entries() {
  local project="$TMP/project-copy-unmarked"
  mkdir -p "$project/.codex/skills/verify" "$project/.agents/skills"
  printf 'project content\n' >"$project/.codex/skills/verify/SKILL.md"
  printf 'project file\n' >"$project/.agents/skills/verify"

  run_cli install project "$project" --copy --force

  assert_file_contents "$project/.codex/skills/verify/SKILL.md" "project content"
  assert_file_contents "$project/.agents/skills/verify" "project file"
  assert_stderr_contains "verify (codex) exists at $project/.codex/skills/verify (not Beislið-owned), skipping"
  assert_stderr_contains "verify (agents) exists at $project/.agents/skills/verify (not Beislið-owned), skipping"
  assert_json_field "$project/.beislid/project-install.json" counts.skipped_copies 2
}

test_project_copy_refreshes_marker_owned_dirs() {
  local project="$TMP/project-copy-refresh-marker"
  mkdir -p "$project"

  run_cli install project "$project" --copy
  printf 'stale copy\n' >"$project/.claude/skills/verify/SKILL.md"
  run_cli install project "$project" --copy

  local expected_refreshes=$(( ${#SKILLS_EXPECTED[@]} * 3 ))
  assert_file_contains "$project/.claude/skills/verify/SKILL.md" "# Check Done"
  assert_stdout_contains "refresh: verify (claude)"
  assert_json_field "$project/.beislid/project-install.json" counts.refreshed_copies "$expected_refreshes"
}

test_project_copy_uses_manifest_when_marker_missing() {
  local project="$TMP/project-copy-refresh-manifest"
  mkdir -p "$project"

  run_cli install project "$project" --copy
  rm "$project/.agents/skills/verify/.beislid-owner.json"
  run_cli install project "$project" --copy

  assert_file_contains "$project/.agents/skills/verify/SKILL.md" "# Check Done"
  assert_json_field "$project/.agents/skills/verify/.beislid-owner.json" owner beislid
}

test_project_copy_manifest_does_not_clobber_recreated_unmarked_dir() {
  local project="$TMP/project-copy-stale-manifest"
  mkdir -p "$project"

  run_cli install project "$project" --copy
  rm -rf "$project/.agents/skills/verify"
  mkdir -p "$project/.agents/skills/verify"
  printf 'project content\n' >"$project/.agents/skills/verify/SKILL.md"
  run_cli install project "$project" --copy --force

  assert_file_contents "$project/.agents/skills/verify/SKILL.md" "project content"
  assert_stderr_contains "verify (agents) exists at $project/.agents/skills/verify (not Beislið-owned), skipping"
}

test_project_copy_uses_marker_when_manifest_missing() {
  local project="$TMP/project-copy-refresh-no-manifest"
  mkdir -p "$project"

  run_cli install project "$project" --copy
  rm "$project/.beislid/project-install.json"
  printf 'stale copy\n' >"$project/.codex/skills/verify/SKILL.md"
  run_cli install project "$project" --copy

  assert_file_contains "$project/.codex/skills/verify/SKILL.md" "# Check Done"
  assert_json_field "$project/.codex/skills/verify/.beislid-owner.json" owner beislid
}

test_project_gitignore_write_is_idempotent() {
  local project="$TMP/project-gitignore"
  mkdir -p "$project"
  printf 'node_modules/\n' >"$project/.gitignore"

  run_cli install project "$project" --copy --write-gitignore
  local first
  first="$(cat "$project/.gitignore")"
  run_cli install project "$project" --copy --write-gitignore
  local second
  second="$(cat "$project/.gitignore")"

  assert_file_contains "$project/.gitignore" "node_modules/"
  assert_file_contains "$project/.gitignore" "# BEGIN Beislið project install"
  assert_file_contains "$project/.gitignore" ".agents/skills/"
  assert_file_contains "$project/.gitignore" ".beislid/project-install.json"
  if [[ "$first" != "$second" ]]; then
    note_fail "expected --write-gitignore to be idempotent"
  fi
  assert_stdout_contains "gitignore: wrote $project/.gitignore"
}

test_project_gitignore_write_replaces_managed_block() {
  local project="$TMP/project-gitignore-replace"
  mkdir -p "$project"
  cat >"$project/.gitignore" <<'EOF_GITIGNORE'
keep-me
# BEGIN Beislið project install
old-entry
# END Beislið project install
EOF_GITIGNORE

  run_cli install project "$project" --write-gitignore

  assert_file_contains "$project/.gitignore" "keep-me"
  assert_file_contains "$project/.gitignore" ".claude/skills/"
  if grep -qF -- "old-entry" "$project/.gitignore"; then
    note_fail "expected managed .gitignore block to be replaced"
  fi
}

test_project_dangling_symlink_autorepair() {
  local project="$TMP/project-dangling"
  mkdir -p "$project/.claude/skills"
  ln -s /nonexistent/old/path/skills/verify "$project/.claude/skills/verify"

  run_cli install project "$project"

  assert_symlink_to "$project/.claude/skills/verify" "$REPO_DIR/skills/verify"
  assert_stdout_contains "fix:  verify (claude) (repaired dangling link; was pointing at"
}

test_project_foreign_symlink_skipped_without_force() {
  local project="$TMP/project-foreign"
  local other="$TMP/other-beislid/skills/verify"
  mkdir -p "$project/.agents/skills" "$other"
  ln -s "$other" "$project/.agents/skills/verify"

  run_cli install project "$project"

  assert_symlink_to "$project/.agents/skills/verify" "$other"
  assert_stderr_contains "verify (agents) symlinked elsewhere"
  assert_json_field "$project/.beislid/project-install.json" counts.skipped_links 1
}

test_project_foreign_symlink_repointed_with_force() {
  local project="$TMP/project-force"
  local other="$TMP/other-beislid/skills/verify"
  mkdir -p "$project/.agents/skills" "$other"
  ln -s "$other" "$project/.agents/skills/verify"

  run_cli install project "$project" --force

  assert_symlink_to "$project/.agents/skills/verify" "$REPO_DIR/skills/verify"
  assert_stdout_contains "fix:  verify (agents) (repointed from"
}

test_project_regular_dir_never_clobbered() {
  local project="$TMP/project-regular"
  mkdir -p "$project/.codex/skills/verify"
  printf 'project content\n' >"$project/.codex/skills/verify/SKILL.md"

  run_cli install project "$project" --force

  assert_not_symlink "$project/.codex/skills/verify"
  assert_file_contents "$project/.codex/skills/verify/SKILL.md" "project content"
  assert_stderr_contains "verify (codex) exists at $project/.codex/skills/verify (not a symlink), skipping"
  assert_json_field "$project/.beislid/project-install.json" counts.skipped_links 1
}

test_project_symlinked_host_dir_is_skipped() {
  local project="$TMP/project-symlinked-host"
  local external="$TMP/external-agents"
  mkdir -p "$project" "$external/skills"
  ln -s "$external" "$project/.agents"

  run_cli install project "$project"

  if [[ -e "$external/skills/verify" || -L "$external/skills/verify" ]]; then
    note_fail "expected project install not to follow symlinked .agents directory"
  fi
  assert_symlink_to "$project/.claude/skills/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$project/.codex/skills/verify" "$REPO_DIR/skills/verify"
  assert_stderr_contains ".agents is a symlink"
  assert_json_field "$project/.beislid/project-install.json" counts.skipped_links "${#SKILLS_EXPECTED[@]}"
}

test_project_workflow_note_prints_when_metadata_dir_blocked() {
  local project="$TMP/project-blocked-metadata"
  mkdir -p "$project"
  printf 'not a dir\n' >"$project/.beislid"

  run_cli install project "$project"

  assert_stderr_contains ".beislid exists at $project/.beislid (not a directory), skipping project manifest"
  assert_stderr_contains "workflow.md not found"
}

test_install_sh_project_rejects_user_only_flags() {
  local project="$TMP/project-user-flags"
  mkdir -p "$project"

  if run_installer --project "$project" --with-security-hooks; then
    note_fail "expected --project with user-only flags to fail"
  fi

  assert_stderr_contains "user-install flags"
  if [[ -e "$project/.beislid/project-install.json" ]]; then
    note_fail "expected rejected project install not to write manifest"
  fi
}

test_repo_ignores_project_manifest_path() {
  if ! git -C "$REAL_REPO_DIR" check-ignore -q .beislid/project-install.json; then
    note_fail "expected repository .gitignore to ignore .beislid/project-install.json"
  fi
}

test_cli_project_status_reports_manifest_and_counts() {
  local project="$TMP/project-status"
  mkdir -p "$project/.beislid"
  printf '<!-- beislid-workflow: v1 -->\n' >"$project/.beislid/workflow.md"
  run_cli install project "$project"

  run_cli status project "$project"

  local expected_skills=${#SKILLS_EXPECTED[@]}
  assert_stdout_contains "beislid project status"
  assert_stdout_contains "project: $project"
  assert_stdout_contains "manifest: $project/.beislid/project-install.json"
  assert_stdout_contains "mode: symlink"
  assert_stdout_contains "source_path: $REPO_DIR"
  assert_stdout_contains "agents: present ($project/.agents/skills)"
  assert_stdout_contains "claude: present ($project/.claude/skills)"
  assert_stdout_contains "codex: present ($project/.codex/skills)"
  assert_stdout_contains "installed_skills: $expected_skills"
}

test_cli_project_status_missing_manifest() {
  local project="$TMP/project-status-missing"
  mkdir -p "$project"

  run_cli status project "$project"

  assert_stdout_contains "beislid project status"
  assert_stdout_contains "manifest: missing ($project/.beislid/project-install.json)"
  assert_stdout_contains "agents: missing ($project/.agents/skills)"
  assert_stdout_contains "installed_skills: 0"
}

test_security_hooks_off_by_default() {
  run_installer
  if [[ -e "$HOOKS/credential_guard.py" ]]; then
    note_fail "expected credential_guard.py not to be installed without --with-security-hooks"
  fi
  if [[ -e "$HOOKS/credential_guard.json" ]]; then
    note_fail "expected credential_guard.json not to be installed without --with-security-hooks"
  fi
}

test_hook_blocks_secret_dump() {
  run_installer --with-security-hooks
  local payload='{"tool_name":"Bash","tool_input":{"command":"cat ~/.ssh/id_rsa"}}'
  local out
  out="$(printf '%s' "$payload" | python3 "$HOOKS/credential_guard.py")"
  if ! grep -q '"permissionDecision": "deny"' <<<"$out"; then
    note_fail "expected hook to deny secret dump, got: $out"
  fi
}

test_update_fast_forwards_and_relinks() {
  setup_update_git_fixture
  run_installer
  local old_head new_head marker
  old_head="$(git -C "$REPO_DIR" rev-parse HEAD)"
  marker="update-fast-forward-marker"
  commit_update_fixture_change "$marker"

  run_installer --update
  new_head="$(git -C "$REPO_DIR" rev-parse HEAD)"
  if [[ "$old_head" == "$new_head" ]]; then
    note_fail "expected update to fast-forward HEAD"
  fi
  assert_stdout_contains "Update:"
  assert_stdout_contains "pull: git -C $REPO_DIR pull --ff-only"
  assert_stdout_contains "restart: $REPO_DIR/install.sh"
  assert_stdout_contains "manifest: $STATE/install.json"
  assert_file_contains "$AGENTS_SKILLS/verify/SKILL.md" "$marker"
  assert_json_field "$STATE/install.json" repo "$REPO_DIR"
  assert_json_field "$STATE/install.json" git_commit "$new_head"
}

test_cli_update_fast_forwards_and_relinks() {
  setup_update_git_fixture
  run_installer
  local old_head new_head marker expected_repo
  old_head="$(git -C "$REPO_DIR" rev-parse HEAD)"
  expected_repo="$(cd -P "$REPO_DIR" && pwd)"
  marker="cli-update-fast-forward-marker"
  commit_update_fixture_change "$marker"

  run_cli update
  new_head="$(git -C "$REPO_DIR" rev-parse HEAD)"
  if [[ "$old_head" == "$new_head" ]]; then
    note_fail "expected CLI update to fast-forward HEAD"
  fi
  assert_stdout_contains "Update:"
  assert_stdout_contains "pull: git -C $expected_repo pull --ff-only"
  assert_stdout_contains "restart: $expected_repo/install.sh"
  assert_file_contains "$AGENTS_SKILLS/verify/SKILL.md" "$marker"
  assert_json_field "$STATE/install.json" repo "$expected_repo"
  assert_json_field "$STATE/install.json" git_commit "$new_head"
}

test_update_aborts_on_dirty_tree() {
  setup_update_git_fixture
  run_installer
  local old_head marker
  old_head="$(git -C "$REPO_DIR" rev-parse HEAD)"
  marker="dirty-tree-remote-marker"
  commit_update_fixture_change "$marker"
  printf '\nlocal dirty change\n' >>"$REPO_DIR/README.md"

  if run_installer --update; then
    note_fail "expected update to fail on dirty tree"
  fi
  if [[ "$(git -C "$REPO_DIR" rev-parse HEAD)" != "$old_head" ]]; then
    note_fail "expected dirty-tree update not to fast-forward HEAD"
  fi
  assert_stderr_contains "cannot update with uncommitted local changes"
  assert_stderr_contains "beislid update"
  assert_file_contains "$AGENTS_SKILLS/verify/SKILL.md" "name: verify"
  if grep -qF -- "$marker" "$AGENTS_SKILLS/verify/SKILL.md"; then
    note_fail "expected dirty-tree update not to relink pulled skill contents"
  fi
}

test_update_preserves_manifest_opt_ins_and_targets() {
  setup_update_git_fixture
  fake_pi
  BEISLID_FAKE_PI_LOG="$TMP/pi-initial.log" run_installer --with-security-hooks --with-pi-show-me
  commit_update_fixture_change "preserve-opt-ins-marker"

  BEISLID_FAKE_PI_LOG="$TMP/pi-update.log" run_installer_without_target_env --update
  assert_json_field "$STATE/install.json" security_hooks "True"
  assert_json_field "$STATE/install.json" pi_show_me "True"
  assert_json_field "$STATE/install.json" skill_dirs.claude "$CLAUDE_SKILLS"
  assert_json_field "$STATE/install.json" skill_dirs.agents "$AGENTS_SKILLS"
  assert_json_field "$STATE/install.json" skill_dirs.codex "$CODEX_SKILLS"
  assert_json_field "$STATE/install.json" hooks_dir "$HOOKS"
  assert_json_field "$STATE/install.json" bin_dir "$BIN_DIR"
  assert_json_field "$STATE/install.json" cli_path "$BIN_DIR/beislid"
  assert_symlink_to "$CLAUDE_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$AGENTS_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$CODEX_SKILLS/verify" "$REPO_DIR/skills/verify"
  assert_symlink_to "$HOOKS/credential_guard.py" "$REPO_DIR/hooks/credential_guard.py"
  assert_symlink_to "$BIN_DIR/beislid" "$REPO_DIR/bin/beislid"
  assert_file_contents "$TMP/pi-update.log" "install $REPO_DIR"
  assert_stdout_contains "preserve: security hooks enabled from install manifest"
  assert_stdout_contains "preserve: pi show-me enabled from install manifest"
  assert_stdout_contains "preserve: Claude skills dir from install manifest"
  assert_stdout_contains "preserve: agents skills dir from install manifest"
  assert_stdout_contains "preserve: Codex skills dir from install manifest"
  assert_stdout_contains "preserve: Claude hooks dir from install manifest"
}

# -----------------------------------------------------------------------------

run_test "fresh install creates all expected symlinks"        test_fresh_install
run_test "re-running is idempotent"                           test_idempotent_rerun
run_test "dangling symlinks are auto-repaired"                test_dangling_symlink_autorepair
run_test "wrong-target symlinks are skipped without --force"  test_wrong_target_skipped_without_force
run_test "wrong-target symlinks are repointed with --force"   test_wrong_target_repointed_with_force
run_test "regular files at dst are never clobbered"           test_regular_file_never_clobbered
run_test "legacy skill symlinks are removed"                  test_legacy_skill_symlinks_are_removed
run_test "install writes manifest"                            test_install_writes_manifest
run_test "CLI is linked by default"                            test_cli_linked_by_default
run_test "install.sh ignores ambient BEISLID_HOME"             test_install_sh_ignores_ambient_beislid_home
run_test "install.sh ignores ambient option flags"             test_install_sh_ignores_ambient_option_flags
run_test "BEISLID_BIN_DIR override is honored"                 test_cli_bin_dir_override
run_test "CLI install warns when bin dir is not on PATH"       test_cli_path_warning
run_test "CLI regular file is never clobbered"                 test_cli_regular_file_never_clobbered
run_test "CLI foreign symlink follows force safety"            test_cli_foreign_symlink_safety
run_test "CLI dangling symlink is repaired"                    test_cli_dangling_symlink_repaired
run_test "status reports installed manifest"                  test_status_after_install
run_test "status reports broken CLI link"                      test_status_reports_broken_cli_link
run_test "status reports enabled hook links"                   test_status_reports_enabled_hook_links
run_test "status handles malformed manifest"                   test_status_handles_malformed_manifest
run_test "CLI help prints command usage"                       test_cli_help
run_test "CLI ignores ambient BEISLID_HOME"                    test_cli_ignores_ambient_beislid_home
run_test "packaged CLI can use BEISLID_HOME fallback"           test_packaged_cli_uses_beislid_home_when_layout_missing
run_test "packaged CLI falls back when run ledger missing"       test_packaged_cli_uses_beislid_home_when_run_ledger_missing
run_test "packaged CLI reports incomplete runtime layout"       test_packaged_cli_reports_incomplete_layout
run_test "packaged CLI reports invalid BEISLID_HOME clearly"     test_packaged_cli_reports_invalid_beislid_home_as_layout_error
run_test "packaged CLI supports Homebrew symlink layout"         test_packaged_cli_supports_homebrew_symlink_layout
run_test "Homebrew formula draft installs runtime subset"       test_homebrew_formula_draft_installs_runtime_subset
run_test "CLI install user delegates to user install"          test_cli_install_user
run_test "CLI ignores ambient option flags"                    test_cli_ignores_ambient_option_flags
run_test "CLI status delegates to status"                      test_cli_status
run_test "workflow-signal noops when unconfigured"            test_workflow_signal_noops_when_unconfigured
run_test "workflow-signal tmux-glance requires tmux"           test_workflow_signal_tmux_glance_requires_tmux
run_test "workflow-signal tmux-glance invokes sink"            test_workflow_signal_tmux_glance_invokes_sink
run_test "workflow-signal skill override can disable"          test_workflow_signal_skill_override_can_disable
run_test "workflow-signal invalid modes noop"                  test_workflow_signal_invalid_modes_noop
run_test "CLI plugin enable lavish writes state"               test_cli_plugin_enable_lavish_writes_state
run_test "CLI plugin status lavish reports light probe"        test_cli_plugin_status_lavish_reports_light_probe
run_test "CLI plugin disable lavish preserves state"           test_cli_plugin_disable_lavish_preserves_state
run_test "CLI plugin status lavish deep check"                 test_cli_plugin_status_lavish_deep_check
run_test "CLI plugin errors are clear"                         test_cli_plugin_errors_are_clear
run_test "v0.2 migration repoints previous install"            test_migrate_v0_2_repoints_previous_manifest_install
run_test "CLI v0.2 migration delegates"                        test_cli_migrate_v0_2_delegates_to_shared_migration
run_test "legacy CLI flags print guidance"                     test_cli_legacy_flag_guidance
run_test "unknown CLI commands print help"                     test_cli_unknown_command
run_test "project install supports explicit CLI target"        test_cli_project_install_explicit_path
run_test "project explicit path inside repo is exact"          test_cli_project_install_explicit_path_inside_repo_is_exact
run_test "project install defaults to git root"                test_cli_project_install_uses_git_root_by_default
run_test "project install defaults to cwd outside git"         test_cli_project_install_uses_cwd_without_git_root
run_test "install.sh --project is compatibility sugar"         test_install_sh_project_compat_explicit_path
run_test "project install copy mode copies skills"             test_cli_project_copy_install_explicit_path
run_test "install.sh --project --copy is compatibility sugar"  test_install_sh_project_copy_compat_explicit_path
run_test "project copy never clobbers unmarked entries"        test_project_copy_never_clobbers_unmarked_entries
run_test "project copy refreshes marker-owned dirs"            test_project_copy_refreshes_marker_owned_dirs
run_test "project copy uses manifest when marker missing"      test_project_copy_uses_manifest_when_marker_missing
run_test "project copy manifest preserves recreated dirs"      test_project_copy_manifest_does_not_clobber_recreated_unmarked_dir
run_test "project copy uses marker when manifest missing"      test_project_copy_uses_marker_when_manifest_missing
run_test "project gitignore write is idempotent"               test_project_gitignore_write_is_idempotent
run_test "project gitignore write replaces managed block"      test_project_gitignore_write_replaces_managed_block
run_test "project install repairs dangling symlinks"           test_project_dangling_symlink_autorepair
run_test "project install skips foreign symlinks"              test_project_foreign_symlink_skipped_without_force
run_test "project install --force repoints symlinks"           test_project_foreign_symlink_repointed_with_force
run_test "project install never clobbers regular dirs"         test_project_regular_dir_never_clobbered
run_test "project install skips symlinked host dirs"           test_project_symlinked_host_dir_is_skipped
run_test "project workflow note survives metadata block"       test_project_workflow_note_prints_when_metadata_dir_blocked
run_test "install.sh --project rejects user-only flags"        test_install_sh_project_rejects_user_only_flags
run_test "repo ignores project manifest path"                  test_repo_ignores_project_manifest_path
run_test "CLI project status reports manifest and counts"      test_cli_project_status_reports_manifest_and_counts
run_test "CLI project status handles missing manifest"         test_cli_project_status_missing_manifest
run_test "pi show-me extension install is opt-in"              test_pi_show_me_is_opt_in
run_test "pi show-me extension installs when requested"        test_pi_show_me_installs_package_when_requested
run_test "security hook is opt-in"                            test_security_hooks_off_by_default
run_test "installed hook blocks a secret dump"                test_hook_blocks_secret_dump
run_test "update fast-forwards and relinks"                   test_update_fast_forwards_and_relinks
run_test "CLI update fast-forwards and relinks"               test_cli_update_fast_forwards_and_relinks
run_test "update aborts on dirty tree"                        test_update_aborts_on_dirty_tree
run_test "update preserves manifest opt-ins and targets"      test_update_preserves_manifest_opt_ins_and_targets

echo
echo "$pass passed, $fail failed"
if (( fail > 0 )); then
  echo "Failures:" >&2
  for n in "${failures[@]}"; do
    echo "  - $n" >&2
  done
  exit 1
fi
