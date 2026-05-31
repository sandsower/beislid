#!/usr/bin/env bash
# Protocol regression checks for action-policy orchestration docs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pass=0
fail=0

note_fail() { echo "    $1" >&2; fail=$((fail + 1)); }
check_contains() {
  local path="$1" needle="$2"
  if grep -qF -- "$needle" "$ROOT/$path"; then
    pass=$((pass + 1))
  else
    note_fail "expected $path to contain: $needle"
  fi
}
check_symlink() {
  local path="$1" target="$2"
  if [[ -L "$ROOT/$path" && "$(readlink "$ROOT/$path")" == "$target" ]]; then
    pass=$((pass + 1))
  else
    note_fail "expected $path to be symlink to $target"
  fi
}

for skill in ready-for-review kickoff review-response implement retro; do
  check_symlink "skills/$skill/action-policy-protocol.md" "../../.beislid/action-policy-protocol.md"
done

check_contains ".beislid/action-policy-protocol.md" 'decision`'
check_contains "skills/ready-for-review/phase-2-gates.md" 'policy-check `git.merge`'
check_contains "skills/ready-for-review/phase-4-submit.md" 'Policy-check push/PR create/draft-ready'
check_contains "skills/kickoff/step-1-ticket.md" 'Evaluate action policy for `lifecycle.kickoff_start.<name>`'
check_contains "skills/kickoff/step-8-ticket-update.md" 'evaluate action policy for `ticket.comment`'
check_contains "skills/implement/SKILL.md" 'Evaluate action policy before workspace writes'
check_contains "skills/retro/SKILL.md" 'evaluate action id `file.write` with class `workspace-write`'
check_contains "skills/review-response/phase-2-fix.md" 'Evaluate action policy for the workspace write'
check_contains "skills/review-response/phase-3-push.md" 'Policy-check `git.push`'
check_contains "docs/configuration.md" "repo-aware orchestrators enforce action policy"

if (( fail > 0 )); then
  echo "$fail action policy protocol check(s) failed; $pass passed" >&2
  exit 1
fi

echo "$pass action policy protocol checks passed"
