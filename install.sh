#!/usr/bin/env bash
# Beislið installer — symlinks skills into user or project host skill dirs,
# installs the beislid CLI for user installs, and optional hooks into
# ~/.claude/hooks/. Idempotent: safe to re-run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BEISLID_HOME="$SCRIPT_DIR"
# shellcheck source=scripts/install_lib.sh
source "$SCRIPT_DIR/scripts/install_lib.sh"

STATUS=0
UPDATE=0
MIGRATE_V0_2=0
PROJECT=0
PROJECT_PATH=""

_usage() {
  cat <<'EOF'
Beislið installer

Usage: ./install.sh [flags]

Flags:
  --project [path]        Install project-local skills into path
                          (default: git root, or cwd outside git)
  --copy                  Copy project-local skills instead of symlinking them
  --write-gitignore       Create or update the managed project .gitignore block
  --with-security-hooks   Install credential_guard hook (opt-in; user install only)
  --strict                Exit nonzero when expected artifacts are skipped
                          or conflicted during install
  --update                Fast-forward this Beislið repo, then re-run install
                          while preserving previous manifest opt-ins
  --migrate-v0.2          One-time migration from pre-v0.2 installs after
                          cloning the clean v0.2 repository history
  --status                Print installed manifest and symlink status
  --force                 Repoint existing symlinks whose target differs
                          from this repo's source. Never clobbers regular
                          files or directories. --repoint is an alias.
  -h, --help              Show this help

Environment:
  CLAUDE_SKILLS_DIR       Target skill dir (default: ~/.claude/skills)
  AGENTS_SKILLS_DIR       Agent-agnostic skill dir (default: ~/.agents/skills)
  CODEX_SKILLS_DIR        Codex skill dir (default: ~/.codex/skills)
  CLAUDE_HOOKS_DIR        Target hook dir (default: ~/.claude/hooks)
  BEISLID_BIN_DIR         Target CLI dir (default: ~/.local/bin)
  BEISLID_STATE_DIR       User install manifest dir (default: ~/.local/state/beislid)

Notes:
  Project installs write <project>/.beislid/project-install.json and do not
  create <project>/.beislid/workflow.md.

  Broken (dangling) symlinks are always repaired automatically — they
  have no content to lose. Symlinks pointing at some other live target
  are kept as-is unless you pass --force. Update aborts when this repo has
  uncommitted local changes.
EOF
}

while (($#)); do
  case "$1" in
    --with-security-hooks) WITH_SECURITY_HOOKS=1 ;;
    --force|--repoint) FORCE=1 ;;
    --strict) STRICT=1 ;;
    --status) STATUS=1 ;;
    --update) UPDATE=1 ;;
    --migrate-v0.2|--migrate-v0.2.0) MIGRATE_V0_2=1 ;;
    --project)
      PROJECT=1
      if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
        PROJECT_PATH="$2"
        shift
      fi
      ;;
    --copy)
      PROJECT_MODE="copy"
      ;;
    --write-gitignore)
      PROJECT_WRITE_GITIGNORE=1
      ;;
    -h|--help)
      _usage
      exit 0
      ;;
    *)
      if [[ "$PROJECT" == 1 && -z "$PROJECT_PATH" ]]; then
        PROJECT_PATH="$1"
      else
        echo "Unknown flag: $1" >&2
        exit 2
      fi
      ;;
  esac
  shift
done

if [[ "$STATUS" == 1 && "$UPDATE" == 1 ]]; then
  echo "error: --status and --update cannot be combined" >&2
  exit 2
fi

if [[ "$MIGRATE_V0_2" == 1 && ( "$STATUS" == 1 || "$UPDATE" == 1 || "$PROJECT" == 1 ) ]]; then
  echo "error: --migrate-v0.2 cannot be combined with --status, --update, or --project" >&2
  exit 2
fi

if [[ "$PROJECT" == 1 && "$UPDATE" == 1 ]]; then
  echo "error: --project and --update cannot be combined" >&2
  exit 2
fi

if [[ "$PROJECT" == 1 && "$STATUS" == 1 ]]; then
  echo "error: --project and --status cannot be combined; use 'beislid status project [path]'" >&2
  exit 2
fi

if [[ "$PROJECT" == 1 && "$WITH_SECURITY_HOOKS" == 1 ]]; then
  echo "error: --with-security-hooks is a user-install flag and cannot be combined with --project" >&2
  exit 2
fi

if [[ "$PROJECT" != 1 && ( "$PROJECT_MODE" == "copy" || "$PROJECT_WRITE_GITIGNORE" == 1 ) ]]; then
  echo "error: --copy and --write-gitignore require --project" >&2
  exit 2
fi

if [[ "$STATUS" == 1 ]]; then
  beislid_status
  exit $?
fi

if [[ "$UPDATE" == 1 ]]; then
  beislid_update_repo
fi

if [[ "$MIGRATE_V0_2" == 1 ]]; then
  beislid_migrate_v0_2
  exit $?
fi

if [[ "$PROJECT" == 1 ]]; then
  beislid_install_project "$PROJECT_PATH"
else
  beislid_install_user
fi
