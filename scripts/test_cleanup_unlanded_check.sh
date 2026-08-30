#!/usr/bin/env bash
# Regression checks for the babysit cleanup unlanded-work test.
#
# The protocol in skills/babysit/cleanup-protocol.md decides unlanded work from
# the intersection of the paths this branch touched with the paths that still
# differ from the default branch. This script builds real squash-merge fixtures
# and runs that recipe, so the check keeps working when the default branch has
# moved on paths the branch never touched.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROTOCOL="skills/babysit/cleanup-protocol.md"

pass=0
fail=0
failures=()
TMP=""

note_fail() { echo "    $1" >&2; }

run_test() {
  local name="$1" fn="$2"
  echo "-- $name"
  TMP="$(mktemp -d)"
  if "$fn"; then
    pass=$((pass + 1))
    echo "   pass"
  else
    fail=$((fail + 1))
    failures+=("$name")
    echo "   FAIL" >&2
  fi
  rm -rf "$TMP"
  TMP=""
}

git_q() { git -c user.name=test -c user.email=test@example.com -c commit.gpgsign=false "$@" >/dev/null 2>&1; }

# Builds remote.git + work/, with `feat` squash-landed on main and an unrelated
# main-only commit on top. Extra args are paths changed on feat that never land.
setup_fixture() {
  local unlanded=()
  (( $# > 0 )) && unlanded=("$@")
  git_q init --bare -b main "$TMP/remote.git"
  git_q clone "$TMP/remote.git" "$TMP/work"
  pushd "$TMP/work" >/dev/null

  mkdir -p src
  echo "base" >src/app.txt
  echo "untouched" >src/other.txt
  git_q add -A
  git_q commit -m "initial"
  git_q push -u origin main

  git_q checkout -b feat
  echo "landed change" >src/app.txt
  local path
  for path in ${unlanded[@]+"${unlanded[@]}"}; do
    mkdir -p "$(dirname "$path")"
    echo "unlanded change" >"$path"
  done
  git_q add -A
  git_q commit -m "feat work"
  git_q push -u origin feat

  # Squash merge feat's landed content onto main, the way a PR merge does.
  git_q checkout main
  git_q checkout feat -- src/app.txt
  git_q commit -m "squash: feat work"

  # An unrelated commit advances main on a path feat never touched.
  echo "unrelated" >src/unrelated.txt
  git_q add -A
  git_q commit -m "unrelated main work"
  git_q push origin main

  git_q checkout feat
  git_q fetch origin main
  popd >/dev/null
}

# The recipe exactly as the protocol states it.
unlanded_paths() {
  local base
  base="$(git -C "$TMP/work" merge-base origin/main HEAD)"
  comm -12 \
    <(git -C "$TMP/work" diff --name-only "$base" HEAD | sort) \
    <(git -C "$TMP/work" diff --name-only origin/main HEAD | sort)
}

assert_equals() {
  local actual="$1" expected="$2" label="$3"
  [[ "$actual" == "$expected" ]] || {
    note_fail "$label: expected [$expected], got [$actual]"
    return 1
  }
}

test_unrelated_default_branch_change_is_not_unlanded() {
  setup_fixture
  # The full-tree comparison the protocol must not gate on is non-empty here:
  # main carries an unrelated commit. That alone must not stop cleanup.
  local full_tree
  full_tree="$(git -C "$TMP/work" diff --name-only origin/main HEAD)"
  [[ -n "$full_tree" ]] || {
    note_fail "fixture is wrong: full-tree diff against origin/main should be non-empty"
    return 1
  }
  assert_equals "$(unlanded_paths)" "" "every branch-touched path landed"
}

test_unlanded_branch_path_is_reported() {
  setup_fixture src/pending.txt
  assert_equals "$(unlanded_paths)" "src/pending.txt" "unlanded branch path"
}

test_glob_magic_path_is_reported() {
  setup_fixture 'pages/[id].tsx'
  assert_equals "$(unlanded_paths)" 'pages/[id].tsx' "glob-magic unlanded path"
}

test_protocol_does_not_gate_on_full_tree_diff() {
  local prereq
  prereq="$(grep -n 'The default branch is freshly fetched' "$REPO_DIR/$PROTOCOL")"
  if grep -qF 'git diff <remote>/<default> HEAD` is empty' "$REPO_DIR/$PROTOCOL"; then
    note_fail "$PROTOCOL still makes an empty full-tree diff a prerequisite: $prereq"
    return 1
  fi
  grep -qF 'Do not make an empty full-tree' "$REPO_DIR/$PROTOCOL" || {
    note_fail "$PROTOCOL should say why the full-tree diff is not the prerequisite"
    return 1
  }
  grep -qF 'comm -12' "$REPO_DIR/$PROTOCOL" || {
    note_fail "$PROTOCOL should keep the path-intersection recipe"
    return 1
  }
}

run_test "unrelated default-branch change is not unlanded work" test_unrelated_default_branch_change_is_not_unlanded
run_test "unlanded branch path is reported" test_unlanded_branch_path_is_reported
run_test "glob-magic unlanded path is reported" test_glob_magic_path_is_reported
run_test "protocol does not gate on the full-tree diff" test_protocol_does_not_gate_on_full_tree_diff

if (( fail > 0 )); then
  echo "$fail cleanup unlanded-check test(s) failed:" >&2
  printf ' - %s\n' "${failures[@]}" >&2
  exit 1
fi

echo "$pass cleanup unlanded-check tests passed"
