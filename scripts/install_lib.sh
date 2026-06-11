#!/usr/bin/env bash
# Shared Beislið installer implementation.
# Sourced by install.sh and bin/beislid; keep command parsing in those entrypoints.

_BEISLID_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${BEISLID_HOME:-}" ]]; then
  SCRIPT_DIR="$(cd "$BEISLID_HOME" && pwd)"
else
  SCRIPT_DIR="$(cd "$_BEISLID_LIB_DIR/.." && pwd)"
fi
BEISLID_HOME="$SCRIPT_DIR"

CLAUDE_SKILLS="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
AGENTS_SKILLS="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
CODEX_SKILLS="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
CLAUDE_HOOKS="${CLAUDE_HOOKS_DIR:-$HOME/.claude/hooks}"
BEISLID_STATE="${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}"
MANIFEST="$BEISLID_STATE/install.json"
BEISLID_BIN_DIR_RESOLVED="${BEISLID_BIN_DIR:-$HOME/.local/bin}"
BEISLID_CLI_PATH="$BEISLID_BIN_DIR_RESOLVED/beislid"

WITH_SECURITY_HOOKS=0
FORCE=0
PROJECT_MODE="symlink"
PROJECT_WRITE_GITIGNORE=0
BEISLID_CLI_LINK_OK=0
BEISLID_LINK_RESULT=""

_current_version() {
  python3 - <<'PY' "$SCRIPT_DIR/.claude-plugin/plugin.json"
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("version", "unknown"))
except Exception:
    print("unknown")
PY
}

_current_commit() {
  git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || echo "unknown"
}

# _link src dst label
# Create dst -> src, with these rules:
#   * symlink already pointing at src             -> no-op
#   * dangling symlink (target gone)              -> repair
#   * symlink pointing at a live, different path  -> repoint only under --force
#   * regular file or directory at dst            -> always skip
# Sets BEISLID_LINK_RESULT to ok/fixed/linked/skipped and returns 0.
_link() {
  local src="$1"
  local dst="$2"
  local label="$3"
  BEISLID_LINK_RESULT="skipped"

  if [[ -L "$dst" ]]; then
    local current
    current="$(readlink "$dst")"
    if [[ "$current" == "$src" ]]; then
      echo "ok:   $label (already linked)"
      BEISLID_LINK_RESULT="ok"
      return 0
    fi
    if [[ ! -e "$dst" ]]; then
      rm "$dst"
      ln -s "$src" "$dst"
      echo "fix:  $label (repaired dangling link; was pointing at $current)"
      BEISLID_LINK_RESULT="fixed"
      return 0
    fi
    if [[ "$FORCE" == 1 ]]; then
      rm "$dst"
      ln -s "$src" "$dst"
      echo "fix:  $label (repointed from $current)"
      BEISLID_LINK_RESULT="fixed"
      return 0
    fi
    echo "warn: $label symlinked elsewhere ($current), skipping (re-run with --force to repoint)" >&2
    return 0
  fi

  if [[ -e "$dst" ]]; then
    echo "warn: $label exists at $dst (not a symlink), skipping" >&2
    echo "      move it aside and re-run if you want the version from this repo" >&2
    return 0
  fi

  ln -s "$src" "$dst"
  echo "link: $label"
  BEISLID_LINK_RESULT="linked"
}

link_skill() {
  local name="$1"
  local src="$SCRIPT_DIR/skills/$name"

  if [[ ! -d "$src" ]]; then
    echo "skip: $name (not in repo yet)"
    return
  fi

  _link "$src" "$CLAUDE_SKILLS/$name" "$name (claude)"
  _link "$src" "$AGENTS_SKILLS/$name" "$name (agents)"
  _link "$src" "$CODEX_SKILLS/$name" "$name (codex)"
}

_legacy_target_is_beislid_skill() {
  local old="$1" target="$2" root
  case "$target" in
    */skills/"$old") ;;
    *) return 1 ;;
  esac
  root="${target%/skills/$old}"
  [[ -f "$root/install.sh" && -f "$root/package.json" ]] || return 1
  grep -q '"name"[[:space:]]*:[[:space:]]*"beislid"' "$root/package.json" 2>/dev/null
}

_cleanup_legacy_skill() {
  local old="$1"
  local target_dir dst current
  for target_dir in "$CLAUDE_SKILLS" "$AGENTS_SKILLS" "$CODEX_SKILLS"; do
    dst="$target_dir/$old"
    if [[ ! -L "$dst" ]]; then
      continue
    fi
    current="$(_symlink_target_abs "$dst" 2>/dev/null || readlink "$dst")"
    if [[ "$current" == "$SCRIPT_DIR/skills/$old" ]] || _legacy_target_is_beislid_skill "$old" "$current"; then
      rm "$dst"
      echo "migrate: removed legacy $old link from $target_dir"
    fi
  done
}

cleanup_legacy_skills() {
  local old
  for old in \
    check-done \
    debug-method \
    design-gate \
    guided-review \
    heard-chef \
    impl-plan \
    prd-to-plan \
    start-ticket \
    ship-it \
    write-prd \
    beislid-blueprint \
    beislid-break-spec \
    beislid-debug \
    beislid-grill-me \
    beislid-heard-chef \
    beislid-implement \
    beislid-kickoff \
    beislid-review \
    beislid-ship-it \
    beislid-spec \
    beislid-verify \
    beislid-walk-the-diff; do
    _cleanup_legacy_skill "$old"
  done
}

link_hook() {
  local name="$1"
  local src="$SCRIPT_DIR/hooks/$name"
  local dst="$CLAUDE_HOOKS/$name"

  mkdir -p "$CLAUDE_HOOKS"

  if [[ ! -f "$src" ]]; then
    echo "skip: hook $name (not in repo yet)"
    return
  fi

  _link "$src" "$dst" "hook $name"
}

_lavish_plugin_state_path() {
  printf '%s/plugins/lavish.json\n' "$BEISLID_STATE"
}

_lavish_plugin_write_state() {
  local enabled="$1" command_value="$2" artifact_root="$3"
  local state_path
  state_path="$(_lavish_plugin_state_path)"
  mkdir -p "$(dirname "$state_path")"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "error: beislid plugin lavish requires python3 to write state" >&2
    exit 1
  fi
  python3 - <<'PY' "$state_path" "$enabled" "$command_value" "$artifact_root"
import json, os, sys
from datetime import datetime, timezone
path, enabled, command, artifact_root = sys.argv[1:]
data = {
    "schema": 1,
    "name": "lavish",
    "provider": "lavish-axi",
    "enabled": enabled == "1",
    "command": command,
    "artifact_root": artifact_root,
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.chmod(path, 0o600)
PY
}

_lavish_plugin_read_field() {
  local field="$1" fallback="$2" state_path
  state_path="$(_lavish_plugin_state_path)"
  if [[ ! -f "$state_path" ]] || ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "$fallback"
    return
  fi
  python3 - <<'PY' "$state_path" "$field" "$fallback"
import json, sys
path, field, fallback = sys.argv[1:]
try:
    data = json.load(open(path, encoding="utf-8"))
    value = data
    for part in field.split("."):
        value = value[part]
except Exception:
    value = fallback
if isinstance(value, bool):
    print("True" if value else "False")
else:
    print(value)
PY
}

_lavish_plugin_first_binary() {
  local command_value="$1"
  if ! command -v python3 >/dev/null 2>&1; then
    printf '\n'
    return 0
  fi
  python3 - <<'PY' "$command_value"
import shlex, sys
try:
    parts = shlex.split(sys.argv[1])
except ValueError:
    parts = []
print(parts[0] if parts else "")
PY
}

_lavish_plugin_deep_check() {
  local command_value="$1"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "deep_check: failed (python3 unavailable)"
    return 1
  fi
  python3 - <<'PY' "$command_value"
import shlex, subprocess, sys
command = sys.argv[1]
try:
    argv = shlex.split(command)
except ValueError as exc:
    print(f"deep_check: failed (invalid command: {exc})")
    sys.exit(1)
if not argv:
    print("deep_check: failed (empty command)")
    sys.exit(1)
try:
    result = subprocess.run([*argv, "--help"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
except FileNotFoundError:
    print(f"deep_check: failed ({argv[0]} not found)")
    sys.exit(1)
except subprocess.TimeoutExpired:
    print("deep_check: failed (timed out)")
    sys.exit(1)
if result.returncode == 0:
    print("deep_check: ok")
    sys.exit(0)
summary = (result.stderr or result.stdout or "").strip().splitlines()
reason = summary[0] if summary else f"exit {result.returncode}"
print(f"deep_check: failed ({reason})")
sys.exit(1)
PY
}

beislid_plugin_lavish_enable() {
  local command_value="npx -y lavish-axi" artifact_root=".lavish"
  while (($#)); do
    case "$1" in
      --command)
        shift
        if [[ -z "${1:-}" ]]; then
          echo "Missing value for --command" >&2
          exit 2
        fi
        command_value="$1"
        ;;
      --artifact-root)
        shift
        if [[ -z "${1:-}" ]]; then
          echo "Missing value for --artifact-root" >&2
          exit 2
        fi
        artifact_root="$1"
        ;;
      -h|--help)
        echo "Usage: beislid plugin enable lavish [--command COMMAND] [--artifact-root PATH]"
        return 0
        ;;
      *)
        echo "Unknown plugin enable flag: $1" >&2
        exit 2
        ;;
    esac
    shift
  done

  _lavish_plugin_write_state 1 "$command_value" "$artifact_root"
  echo "Lavish plugin enabled"
  echo "  state: $(_lavish_plugin_state_path)"
  echo "  command: $command_value"
  echo "  artifact_root: $artifact_root"
  echo "  note: default command is 'npx -y lavish-axi'. First real use or 'beislid plugin status lavish --check' may touch npm, network, and local package cache. Lavish runtime behavior is owned by Lavish; configure a pinned/local command if your environment needs that boundary."
}

beislid_plugin_lavish_disable() {
  if (($#)); then
    case "${1:-}" in
      -h|--help)
        echo "Usage: beislid plugin disable lavish"
        return 0
        ;;
      *)
        echo "Unknown plugin disable flag: $1" >&2
        exit 2
        ;;
    esac
  fi
  local command_value artifact_root
  command_value="$(_lavish_plugin_read_field command "npx -y lavish-axi")"
  artifact_root="$(_lavish_plugin_read_field artifact_root ".lavish")"
  _lavish_plugin_write_state 0 "$command_value" "$artifact_root"
  echo "Lavish plugin disabled"
  echo "  state: $(_lavish_plugin_state_path)"
}

beislid_plugin_lavish_status() {
  local deep_check=0
  while (($#)); do
    case "$1" in
      --check) deep_check=1 ;;
      -h|--help)
        echo "Usage: beislid plugin status lavish [--check]"
        return 0
        ;;
      *)
        echo "Unknown plugin status flag: $1" >&2
        exit 2
        ;;
    esac
    shift
  done

  local state_path enabled command_value artifact_root binary
  state_path="$(_lavish_plugin_state_path)"
  enabled="$(_lavish_plugin_read_field enabled False)"
  command_value="$(_lavish_plugin_read_field command "npx -y lavish-axi")"
  artifact_root="$(_lavish_plugin_read_field artifact_root ".lavish")"
  binary="$(_lavish_plugin_first_binary "$command_value")"

  echo "beislid plugin status lavish"
  echo "  state: $state_path"
  echo "  enabled: $enabled"
  echo "  provider: lavish-axi"
  echo "  command: $command_value"
  echo "  artifact_root: $artifact_root"
  if [[ -n "$binary" ]] && command -v "$binary" >/dev/null 2>&1; then
    echo "  light_probe: ok ($binary)"
  elif [[ -n "$binary" ]]; then
    echo "  light_probe: missing ($binary)"
  else
    echo "  light_probe: failed (empty command)"
  fi
  if [[ "$deep_check" == 1 ]]; then
    echo "  deep_check_note: may invoke the configured Lavish command and touch npm/network/cache"
    printf '  '
    _lavish_plugin_deep_check "$command_value" || return 1
  fi
}

_workflow_signal_usage() {
  cat <<'USAGE'
Usage:
  beislid workflow-signal emit <working|blocked|waiting|verify|review|done|explore> [--skill NAME] [--phase NAME] [--event NAME] [--repo PATH]
  beislid workflow-signal status [--skill NAME] [--repo PATH]
USAGE
}

_workflow_signal_state_valid() {
  case "$1" in
    working|blocked|waiting|verify|review|done|explore) return 0 ;;
    *) return 1 ;;
  esac
}

_workflow_signal_tmux_glance_state() {
  case "$1" in
    explore) printf '%s\n' working ;;
    *) printf '%s\n' "$1" ;;
  esac
}

_workflow_signal_repo_root() {
  local requested="$1"
  if [[ -n "$requested" ]]; then
    if [[ -d "$requested" ]]; then
      git -C "$requested" rev-parse --show-toplevel 2>/dev/null || (cd "$requested" && pwd)
      return 0
    fi
    printf '%s\n' "$requested"
    return 0
  fi
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

_workflow_signal_config_lines() {
  local repo="$1" skill="$2"
  local workflow="$repo/.beislid/workflow.md"
  if [[ ! -f "$workflow" ]] || ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi
  python3 - <<'PY' "$workflow" "$skill"
import re, shlex, sys
path, skill = sys.argv[1:]
try:
    lines = open(path, encoding="utf-8").read().splitlines()
except Exception:
    sys.exit(0)
block = []
in_block = False
for line in lines:
    if not in_block and line.strip().startswith("```beislid:workflow_signals"):
        in_block = True
        continue
    if in_block and line.strip().startswith("```"):
        break
    if in_block:
        block.append(line.rstrip("\n"))
if not block:
    sys.exit(0)
mode = "auto"
sinks = []
skills = {}
section = None
current_sink = None
for raw in block:
    if not raw.strip() or raw.lstrip().startswith("#"):
        continue
    indent = len(raw) - len(raw.lstrip(" "))
    stripped = raw.strip()
    if indent == 0 and stripped.startswith("mode:"):
        mode = stripped.split(":", 1)[1].strip().strip("'\"") or mode
        section = None
        current_sink = None
        continue
    if indent == 0 and stripped == "sinks:":
        section = "sinks"
        current_sink = None
        continue
    if indent == 0 and stripped == "skills:":
        section = "skills"
        current_sink = None
        continue
    if section == "sinks":
        if stripped.startswith("- "):
            current_sink = {}
            item = stripped[2:].strip()
            if item.startswith("type:"):
                current_sink["type"] = item.split(":", 1)[1].strip().strip("'\"")
            sinks.append(current_sink)
            continue
        if current_sink is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current_sink[key.strip()] = value.strip().strip("'\"")
            continue
    if section == "skills" and ":" in stripped:
        key, value = stripped.split(":", 1)
        skills[key.strip()] = value.strip().strip("'\"")
if not sinks:
    # No implicit default sink: a configured signal surface must name sinks.
    sinks = []
skill_mode = skills.get(skill, mode) if skill else mode
print("configured=1")
print("mode=" + shlex.quote(mode))
print("skill_mode=" + shlex.quote(skill_mode))
for sink in sinks:
    t = sink.get("type", "")
    if t:
        print("sink=" + shlex.quote(t))
PY
}

_workflow_signal_write_file() {
  # File sink — unconditional, runs regardless of workflow_signals config.
  # Path: ${BEISLID_STATE_DIR}/signals/<repo_hash>/<branch_slug>
  # Format: line 1 = absolute worktree path, line 2 = "<state> <skill|-> <phase|-> <iso-ts>"
  # On state=done the file is removed (missing file == idle/done).
  local repo="$1" state="$2" skill="${3:-}" phase="${4:-}"
  local state_dir repo_hash branch_slug signal_dir signal_file ts
  state_dir="${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}"
  repo_hash="$(git -C "$repo" rev-list --max-parents=0 HEAD 2>/dev/null | head -c 12)"
  [[ -n "$repo_hash" ]] || return 0
  branch_slug="$(git -C "$repo" branch --show-current 2>/dev/null | tr '/' '-')"
  [[ -n "$branch_slug" ]] || return 0
  signal_dir="$state_dir/signals/$repo_hash"
  signal_file="$signal_dir/$branch_slug"
  if [[ "$state" == "done" ]]; then
    rm -f "$signal_file"
    return 0
  fi
  mkdir -p "$signal_dir" || return 0
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf '')"
  printf '%s\n%s %s %s %s\n' \
    "$repo" \
    "$state" \
    "${skill:--}" \
    "${phase:--}" \
    "$ts" \
    > "$signal_file"
}

beislid_workflow_signal() {
  local subcmd="${1:-}"
  shift || true
  case "$subcmd" in
    emit)
      local state="${1:-}" skill="" phase="" event="" repo_arg=""
      if [[ -z "$state" ]]; then
        _workflow_signal_usage >&2
        return 2
      fi
      shift
      if ! _workflow_signal_state_valid "$state"; then
        echo "Unknown workflow signal state: $state" >&2
        _workflow_signal_usage >&2
        return 2
      fi
      while (($#)); do
        case "$1" in
          --skill) shift; skill="${1:-}" ;;
          --phase) shift; phase="${1:-}" ;;
          --event) shift; event="${1:-}" ;;
          --repo) shift; repo_arg="${1:-}" ;;
          -h|--help) _workflow_signal_usage; return 0 ;;
          *) echo "Unknown workflow-signal emit flag: $1" >&2; return 2 ;;
        esac
        if [[ -z "${1:-}" ]]; then
          echo "Missing value for workflow-signal flag" >&2
          return 2
        fi
        shift
      done
      local repo config mode="off" skill_mode="off" line saw_config=0
      repo="$(_workflow_signal_repo_root "$repo_arg")"
      # File sink: always write, not gated on workflow_signals config.
      _workflow_signal_write_file "$repo" "$state" "$skill" "$phase"
      config="$(_workflow_signal_config_lines "$repo" "$skill")"
      while IFS= read -r line; do
        case "$line" in
          configured=1) saw_config=1 ;;
          mode=*) mode="${line#mode=}" ;;
          skill_mode=*) skill_mode="${line#skill_mode=}" ;;
        esac
      done <<<"$config"
      [[ "$saw_config" == 1 && "$mode" == "auto" && "$skill_mode" == "auto" ]] || return 0
      while IFS= read -r line; do
        case "$line" in
          sink=tmux-glance)
            [[ -n "${TMUX:-}" ]] || continue
            command -v tmux-glance >/dev/null 2>&1 || continue
            tmux-glance "$(_workflow_signal_tmux_glance_state "$state")" >/dev/null 2>&1 || true
            ;;
        esac
      done <<<"$config"
      ;;
    status)
      local skill="" repo_arg=""
      while (($#)); do
        case "$1" in
          --skill) shift; skill="${1:-}" ;;
          --repo) shift; repo_arg="${1:-}" ;;
          -h|--help) _workflow_signal_usage; return 0 ;;
          *) echo "Unknown workflow-signal status flag: $1" >&2; return 2 ;;
        esac
        if [[ -z "${1:-}" ]]; then
          echo "Missing value for workflow-signal flag" >&2
          return 2
        fi
        shift
      done
      local repo config line saw_config=0
      repo="$(_workflow_signal_repo_root "$repo_arg")"
      config="$(_workflow_signal_config_lines "$repo" "$skill")"
      echo "beislid workflow-signal status"
      echo "  repo: $repo"
      while IFS= read -r line; do
        [[ "$line" == configured=1 ]] && saw_config=1
      done <<<"$config"
      if [[ "$saw_config" != 1 ]]; then
        echo "  workflow_signals: not configured"
        return 0
      fi
      while IFS= read -r line; do
        case "$line" in
          mode=*) echo "  mode: ${line#mode=}" ;;
          skill_mode=*) [[ -n "$skill" ]] && echo "  skill_mode: ${line#skill_mode=}" ;;
          sink=*) echo "  sink: ${line#sink=}" ;;
        esac
      done <<<"$config"
      ;;
    ""|-h|--help)
      _workflow_signal_usage
      ;;
    *)
      echo "Unknown workflow-signal subcommand: $subcmd" >&2
      _workflow_signal_usage >&2
      return 2
      ;;
  esac
}

_path_contains_dir() {
  local dir="$1"
  case ":${PATH:-}:" in
    *":$dir:"*) return 0 ;;
    *) return 1 ;;
  esac
}

install_cli_link() {
  local src="$SCRIPT_DIR/bin/beislid"
  local dst="$BEISLID_CLI_PATH"

  mkdir -p "$BEISLID_BIN_DIR_RESOLVED"

  if [[ ! -f "$src" ]]; then
    echo "skip: beislid CLI (not in repo yet)"
    BEISLID_CLI_LINK_OK=0
    return
  fi

  _link "$src" "$dst" "beislid CLI"
  if [[ "$BEISLID_LINK_RESULT" != "skipped" ]]; then
    BEISLID_CLI_LINK_OK=1
  else
    BEISLID_CLI_LINK_OK=0
  fi

  if ! _path_contains_dir "$BEISLID_BIN_DIR_RESOLVED"; then
    echo "warn: $BEISLID_BIN_DIR_RESOLVED is not on PATH; add it to run 'beislid' directly" >&2
  fi
}

_write_manifest() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "warn: python3 not found; skipping install manifest" >&2
    return
  fi
  mkdir -p "$BEISLID_STATE"
  local version commit installed_at
  version="$(_current_version)"
  commit="$(_current_commit)"
  installed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - <<'PY' "$MANIFEST" "$installed_at" "$SCRIPT_DIR" "$version" "$commit" "$CLAUDE_SKILLS" "$AGENTS_SKILLS" "$CODEX_SKILLS" "$CLAUDE_HOOKS" "$WITH_SECURITY_HOOKS" "$BEISLID_CLI_LINK_OK" "$BEISLID_BIN_DIR_RESOLVED" "$BEISLID_CLI_PATH"
import json, sys
manifest, installed_at, repo, version, commit, claude, agents, codex, hooks, security, cli_ok, bin_dir, cli_path = sys.argv[1:]
data = {
    "installed_at": installed_at,
    "repo": repo,
    "version": version,
    "git_commit": commit,
    "skill_dirs": {
        "claude": claude,
        "agents": agents,
        "codex": codex,
    },
    "hooks_dir": hooks,
    "security_hooks": security == "1",
}
if cli_ok == "1":
    data["bin_dir"] = bin_dir
    data["cli_path"] = cli_path
with open(manifest, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
  echo "manifest: $MANIFEST"
}

beislid_status() {
  echo "beislid status"
  local manifest_security_hooks=0
  if [[ -f "$MANIFEST" ]]; then
    if command -v python3 >/dev/null 2>&1; then
      local manifest_values
      manifest_values="$(python3 - <<'PY' "$MANIFEST" "$SCRIPT_DIR"
import json, subprocess, sys
manifest, repo = sys.argv[1:]
try:
    data = json.load(open(manifest, encoding="utf-8"))
except Exception:
    print(f"  manifest: unreadable ({manifest})")
    print("  installed_at: unknown")
    print("  version: unknown")
    print("  installed_commit: unknown")
    print("  current_commit: unknown")
    print("  repo: unknown")
    print("  security_hooks: False")
    print("__BEISLID_SECURITY_HOOKS__=0")
    sys.exit(0)
try:
    head = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
except Exception:
    head = "unknown"
print(f"  manifest: {manifest}")
print(f"  installed_at: {data.get('installed_at', 'unknown')}")
print(f"  version: {data.get('version', 'unknown')}")
print(f"  installed_commit: {data.get('git_commit', 'unknown')}")
print(f"  current_commit: {head}")
print(f"  repo: {data.get('repo', 'unknown')}")
if data.get("cli_path"):
    print(f"  cli_path: {data.get('cli_path')}")
print(f"  security_hooks: {data.get('security_hooks', False)}")
print("__BEISLID_SECURITY_HOOKS__=" + ("1" if data.get("security_hooks") is True else "0"))
PY
)"
      manifest_security_hooks="$(printf '%s\n' "$manifest_values" | sed -n 's/^__BEISLID_SECURITY_HOOKS__=//p' | tail -n 1)"
      printf '%s\n' "$manifest_values" | grep -v '^__BEISLID_SECURITY_HOOKS__='
    else
      echo "  manifest: present but python3 is unavailable ($MANIFEST)"
    fi
  else
    echo "  manifest: missing ($MANIFEST)"
  fi

  local failed=0 dir skill expected
  for dir in "$CLAUDE_SKILLS" "$AGENTS_SKILLS" "$CODEX_SKILLS"; do
    echo "  skills: $dir"
    for skill_dir in "$SCRIPT_DIR"/skills/*/; do
      [[ -d "$skill_dir" ]] || continue
      skill="$(basename "$skill_dir")"
      expected="$SCRIPT_DIR/skills/$skill"
      if [[ -L "$dir/$skill" && "$(readlink "$dir/$skill")" == "$expected" ]]; then
        echo "    ✓ $skill"
      else
        echo "    ✗ $skill"
        failed=1
      fi
    done
  done

  echo "  cli: $BEISLID_CLI_PATH"
  expected="$SCRIPT_DIR/bin/beislid"
  if [[ -L "$BEISLID_CLI_PATH" && "$(readlink "$BEISLID_CLI_PATH")" == "$expected" ]]; then
    echo "    ✓ beislid"
  else
    echo "    ✗ beislid"
    failed=1
  fi

  if [[ "$manifest_security_hooks" == 1 ]]; then
    echo "  hooks: $CLAUDE_HOOKS"
    for hook in credential_guard.py credential_guard.json; do
      expected="$SCRIPT_DIR/hooks/$hook"
      if [[ -L "$CLAUDE_HOOKS/$hook" && "$(readlink "$CLAUDE_HOOKS/$hook")" == "$expected" ]]; then
        echo "    ✓ $hook"
      else
        echo "    ✗ $hook"
        failed=1
      fi
    done
  fi

  return "$failed"
}

_project_target_from_arg() {
  local requested="${1:-}"
  local target

  if [[ -n "$requested" ]]; then
    if [[ ! -d "$requested" ]]; then
      echo "error: project target does not exist or is not a directory: $requested" >&2
      return 1
    fi
    target="$(cd "$requested" && pwd)"
  else
    if target="$(git rev-parse --show-toplevel 2>/dev/null)"; then
      :
    else
      target="$(pwd)"
      echo "warn: not inside a git repo; using current directory: $target" >&2
    fi
  fi

  if ! git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "warn: project target is not inside a git repo; continuing: $target" >&2
  fi

  printf '%s\n' "$target"
}

_project_manifest_path() {
  printf '%s/.beislid/project-install.json\n' "$1"
}

_write_project_manifest() {
  local project="$1" agents_dir="$2" claude_dir="$3" codex_dir="$4" mode="$5" installed_links="$6" skipped_links="$7" installed_copies="$8" refreshed_copies="$9" skipped_copies="${10}"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "warn: python3 not found; skipping project install manifest" >&2
    return
  fi

  local manifest version commit installed_at skill_count
  manifest="$(_project_manifest_path "$project")"
  version="$(_current_version)"
  commit="$(_current_commit)"
  installed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  skill_count=0
  local skill_dir
  for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_count=$((skill_count + 1))
  done

  python3 - <<'PY' "$manifest" "$installed_at" "$SCRIPT_DIR" "$version" "$commit" "$project" "$agents_dir" "$claude_dir" "$codex_dir" "$mode" "$installed_links" "$skipped_links" "$installed_copies" "$refreshed_copies" "$skipped_copies" "$skill_count" "${PROJECT_OWNED_AGENTS:-}" "${PROJECT_OWNED_CLAUDE:-}" "${PROJECT_OWNED_CODEX:-}" "${PROJECT_FINGERPRINT_AGENTS:-}" "${PROJECT_FINGERPRINT_CLAUDE:-}" "${PROJECT_FINGERPRINT_CODEX:-}"
import json, sys
(
    manifest,
    installed_at,
    source_path,
    version,
    commit,
    project_path,
    agents_dir,
    claude_dir,
    codex_dir,
    mode,
    installed_links,
    skipped_links,
    installed_copies,
    refreshed_copies,
    skipped_copies,
    skill_count,
    owned_agents,
    owned_claude,
    owned_codex,
    fingerprint_agents,
    fingerprint_claude,
    fingerprint_codex,
) = sys.argv[1:]
counts = {"skills": int(skill_count)}
if mode == "copy":
    counts.update({
        "installed_copies": int(installed_copies),
        "refreshed_copies": int(refreshed_copies),
        "skipped_copies": int(skipped_copies),
    })
else:
    counts.update({
        "installed_links": int(installed_links),
        "skipped_links": int(skipped_links),
    })

def split_owned(value):
    return [item for item in value.split(":") if item]

data = {
    "installed_at": installed_at,
    "source_path": source_path,
    "version": version,
    "git_commit": commit,
    "mode": mode,
    "project_path": project_path,
    "targets": {
        "agents": agents_dir,
        "claude": claude_dir,
        "codex": codex_dir,
    },
    "counts": counts,
}
if mode == "copy":
    def split_fingerprints(value):
        result = {}
        for item in value.split(":"):
            if not item or "=" not in item:
                continue
            skill, fingerprint = item.split("=", 1)
            result[skill] = fingerprint
        return result

    data["copy"] = {
        "ownership_marker": ".beislid-owner.json",
        "owned_copies": {
            "agents": split_owned(owned_agents),
            "claude": split_owned(owned_claude),
            "codex": split_owned(owned_codex),
        },
        "fingerprints": {
            "agents": split_fingerprints(fingerprint_agents),
            "claude": split_fingerprints(fingerprint_claude),
            "codex": split_fingerprints(fingerprint_codex),
        },
    }
with open(manifest, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
  echo "manifest: $manifest"
}

_project_link_and_count() {
  local src="$1" dst="$2" label="$3"
  _link "$src" "$dst" "$label"
  case "$BEISLID_LINK_RESULT" in
    skipped) PROJECT_SKIPPED_LINKS=$((PROJECT_SKIPPED_LINKS + 1)) ;;
    *) PROJECT_INSTALLED_LINKS=$((PROJECT_INSTALLED_LINKS + 1)) ;;
  esac
}

_project_record_owned_copy() {
  local host="$1" skill="$2" fingerprint="$3"
  case "$host" in
    agents)
      PROJECT_OWNED_AGENTS="${PROJECT_OWNED_AGENTS:-}:$skill"
      PROJECT_FINGERPRINT_AGENTS="${PROJECT_FINGERPRINT_AGENTS:-}:$skill=$fingerprint"
      ;;
    claude)
      PROJECT_OWNED_CLAUDE="${PROJECT_OWNED_CLAUDE:-}:$skill"
      PROJECT_FINGERPRINT_CLAUDE="${PROJECT_FINGERPRINT_CLAUDE:-}:$skill=$fingerprint"
      ;;
    codex)
      PROJECT_OWNED_CODEX="${PROJECT_OWNED_CODEX:-}:$skill"
      PROJECT_FINGERPRINT_CODEX="${PROJECT_FINGERPRINT_CODEX:-}:$skill=$fingerprint"
      ;;
  esac
}

_project_dir_fingerprint() {
  local dir="$1"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - <<'PY' "$dir"
import hashlib, os, sys
root = sys.argv[1]
h = hashlib.sha256()
try:
    for current, dirs, files in os.walk(root):
        dirs.sort()
        files.sort()
        for name in files:
            if name == ".beislid-owner.json":
                continue
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            h.update(b"file\0")
            h.update(rel.encode("utf-8", "surrogateescape"))
            h.update(b"\0")
            if os.path.islink(path):
                h.update(b"link\0")
                h.update(os.readlink(path).encode("utf-8", "surrogateescape"))
            else:
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
            h.update(b"\0")
except Exception:
    sys.exit(1)
print(h.hexdigest())
PY
}

_project_copy_marker_owns() {
  local dst="$1" skill="$2"
  local marker="$dst/.beislid-owner.json"
  [[ -f "$marker" ]] || return 1
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' "$marker" "$skill"
import json, sys
marker, skill = sys.argv[1:]
try:
    data = json.load(open(marker, encoding="utf-8"))
except Exception:
    sys.exit(1)
if data.get("owner") == "beislid" and data.get("mode") == "copy" and data.get("skill") == skill:
    sys.exit(0)
sys.exit(1)
PY
    return $?
  fi
  grep -q '"owner"[[:space:]]*:[[:space:]]*"beislid"' "$marker" && \
    grep -q '"mode"[[:space:]]*:[[:space:]]*"copy"' "$marker" && \
    grep -q '"skill"[[:space:]]*:[[:space:]]*"'"$skill"'"' "$marker"
}

_project_manifest_owns_copy() {
  local project="$1" host="$2" skill="$3" dst="$4" manifest current_fingerprint
  manifest="$(_project_manifest_path "$project")"
  [[ -f "$manifest" ]] || return 1
  command -v python3 >/dev/null 2>&1 || return 1
  current_fingerprint="$(_project_dir_fingerprint "$dst")" || return 1
  python3 - <<'PY' "$manifest" "$host" "$skill" "$current_fingerprint"
import json, sys
manifest, host, skill, current_fingerprint = sys.argv[1:]
try:
    data = json.load(open(manifest, encoding="utf-8"))
except Exception:
    sys.exit(1)
copy = data.get("copy") or {}
owned = (copy.get("owned_copies") or {}).get(host) or []
fingerprints = (copy.get("fingerprints") or {}).get(host) or {}
expected_fingerprint = fingerprints.get(skill)
if (
    data.get("mode") == "copy"
    and skill in owned
    and expected_fingerprint
    and expected_fingerprint == current_fingerprint
):
    sys.exit(0)
sys.exit(1)
PY
}

_project_copy_is_owned() {
  local project="$1" host="$2" skill="$3" dst="$4"
  _project_copy_marker_owns "$dst" "$skill" || _project_manifest_owns_copy "$project" "$host" "$skill" "$dst"
}

_write_project_copy_marker() {
  local dst="$1" project="$2" host="$3" skill="$4" src="$5" fingerprint="$6"
  if command -v python3 >/dev/null 2>&1; then
    local version commit installed_at
    version="$(_current_version)"
    commit="$(_current_commit)"
    installed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - <<'PY' "$dst/.beislid-owner.json" "$installed_at" "$SCRIPT_DIR" "$src" "$project" "$host" "$skill" "$version" "$commit" "$fingerprint"
import json, sys
marker, installed_at, source_path, source_skill_path, project_path, host, skill, version, commit, fingerprint = sys.argv[1:]
data = {
    "owner": "beislid",
    "mode": "copy",
    "skill": skill,
    "host": host,
    "source_path": source_path,
    "source_skill_path": source_skill_path,
    "project_path": project_path,
    "version": version,
    "git_commit": commit,
    "installed_at": installed_at,
    "copy_fingerprint": fingerprint,
}
with open(marker, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
  else
    cat >"$dst/.beislid-owner.json" <<EOF
{"owner":"beislid","mode":"copy","skill":"$skill","host":"$host","source_path":"$SCRIPT_DIR","source_skill_path":"$src","project_path":"$project","copy_fingerprint":"$fingerprint"}
EOF
  fi
}

_project_copy_skill_dir() {
  local src="$1" dst="$2" label="$3" project="$4" host="$5" skill="$6" action="$7" fingerprint
  rm -rf "$dst"
  mkdir -p "$dst"
  cp -R "$src/." "$dst/"
  fingerprint="$(_project_dir_fingerprint "$dst")" || fingerprint=""
  _write_project_copy_marker "$dst" "$project" "$host" "$skill" "$src" "$fingerprint"
  _project_record_owned_copy "$host" "$skill" "$fingerprint"
  case "$action" in
    refresh)
      echo "refresh: $label"
      PROJECT_REFRESHED_COPIES=$((PROJECT_REFRESHED_COPIES + 1))
      ;;
    fix)
      echo "fix:  $label (replaced symlink with copy)"
      PROJECT_INSTALLED_COPIES=$((PROJECT_INSTALLED_COPIES + 1))
      ;;
    *)
      echo "copy: $label"
      PROJECT_INSTALLED_COPIES=$((PROJECT_INSTALLED_COPIES + 1))
      ;;
  esac
}

_project_copy_and_count() {
  local project="$1" host="$2" src="$3" dst="$4" label="$5" skill="$6"

  if [[ -L "$dst" ]]; then
    local current
    current="$(readlink "$dst")"
    if [[ ! -e "$dst" || "$FORCE" == 1 ]]; then
      rm "$dst"
      _project_copy_skill_dir "$src" "$dst" "$label" "$project" "$host" "$skill" "fix"
      return 0
    fi
    echo "warn: $label symlinked at $dst ($current), skipping (re-run with --force to replace with copy)" >&2
    PROJECT_SKIPPED_COPIES=$((PROJECT_SKIPPED_COPIES + 1))
    return 0
  fi

  if [[ -d "$dst" ]]; then
    if _project_copy_is_owned "$project" "$host" "$skill" "$dst"; then
      _project_copy_skill_dir "$src" "$dst" "$label" "$project" "$host" "$skill" "refresh"
    else
      echo "warn: $label exists at $dst (not Beislið-owned), skipping" >&2
      PROJECT_SKIPPED_COPIES=$((PROJECT_SKIPPED_COPIES + 1))
    fi
    return 0
  fi

  if [[ -e "$dst" ]]; then
    echo "warn: $label exists at $dst (not Beislið-owned), skipping" >&2
    PROJECT_SKIPPED_COPIES=$((PROJECT_SKIPPED_COPIES + 1))
    return 0
  fi

  _project_copy_skill_dir "$src" "$dst" "$label" "$project" "$host" "$skill" "copy"
}

_project_gitignore_block() {
  cat <<'EOF'
# BEGIN Beislið project install
.agents/skills/
.claude/skills/
.codex/skills/
.beislid/project-install.json
# END Beislið project install
EOF
}

_write_project_gitignore() {
  local project="$1"
  local gitignore="$project/.gitignore"
  if [[ -L "$gitignore" ]]; then
    echo "warn: .gitignore is a symlink at $gitignore, skipping managed block to avoid writing outside the project" >&2
    return 1
  fi
  if [[ -e "$gitignore" && ! -f "$gitignore" ]]; then
    echo "warn: .gitignore exists at $gitignore (not a file), skipping managed block" >&2
    return 1
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' "$gitignore"
import re, sys
path = sys.argv[1]
block = """# BEGIN Beislið project install
.agents/skills/
.claude/skills/
.codex/skills/
.beislid/project-install.json
# END Beislið project install
"""
try:
    with open(path, encoding="utf-8") as f:
        existing = f.read()
except FileNotFoundError:
    existing = ""
pattern = re.compile(r"# BEGIN Beislið project install\n.*?# END Beislið project install\n?", re.S)
if pattern.search(existing):
    content = pattern.sub(block, existing)
else:
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    content = prefix + block
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
PY
  else
    if [[ -f "$gitignore" ]] && grep -q '^# BEGIN Beislið project install$' "$gitignore" && grep -q '^# END Beislið project install$' "$gitignore"; then
      awk '
        function block() {
          print "# BEGIN Beislið project install"
          print ".agents/skills/"
          print ".claude/skills/"
          print ".codex/skills/"
          print ".beislid/project-install.json"
          print "# END Beislið project install"
        }
        /^# BEGIN Beislið project install$/ { if (!done) { block(); done=1 } inblock=1; next }
        /^# END Beislið project install$/ { inblock=0; next }
        !inblock { print }
      ' "$gitignore" >"$gitignore.tmp"
    else
      {
        [[ -f "$gitignore" ]] && cat "$gitignore"
        echo
        _project_gitignore_block
      } >"$gitignore.tmp"
    fi
    mv "$gitignore.tmp" "$gitignore"
  fi
  echo "gitignore: wrote $gitignore"
}

_project_gitignore_guidance() {
  local project="$1"
  echo
  echo "Gitignore:"
  if [[ "$PROJECT_WRITE_GITIGNORE" == 1 ]]; then
    _write_project_gitignore "$project" || true
  else
    echo "Suggested managed block (not written; re-run with --write-gitignore to manage it):"
    _project_gitignore_block
  fi
}

_ensure_project_skill_dir() {
  local project="$1" host="$2"
  local root="$project/.$host"
  local dir="$root/skills"

  if [[ -L "$root" ]]; then
    echo "warn: .$host is a symlink at $root, skipping $host skills to avoid writing outside the project" >&2
    return 1
  fi
  if [[ -e "$root" && ! -d "$root" ]]; then
    echo "warn: .$host exists at $root (not a directory), skipping $host skills" >&2
    return 1
  fi
  mkdir -p "$root"

  if [[ -L "$dir" ]]; then
    echo "warn: .$host/skills is a symlink at $dir, skipping $host skills to avoid writing outside the project" >&2
    return 1
  fi
  if [[ -e "$dir" && ! -d "$dir" ]]; then
    echo "warn: .$host/skills exists at $dir (not a directory), skipping $host skills" >&2
    return 1
  fi
  mkdir -p "$dir"
}

_ensure_project_metadata_dir() {
  local project="$1"
  local dir="$project/.beislid"

  if [[ -L "$dir" ]]; then
    echo "warn: .beislid is a symlink at $dir, skipping project manifest to avoid writing outside the project" >&2
    return 1
  fi
  if [[ -e "$dir" && ! -d "$dir" ]]; then
    echo "warn: .beislid exists at $dir (not a directory), skipping project manifest" >&2
    return 1
  fi
  mkdir -p "$dir"
}

beislid_install_project() {
  local requested="${1:-}"
  local project
  if ! project="$(_project_target_from_arg "$requested")"; then
    return 1
  fi

  local agents_dir="$project/.agents/skills"
  local claude_dir="$project/.claude/skills"
  local codex_dir="$project/.codex/skills"
  local agents_active=0 claude_active=0 codex_active=0 manifest_active=0

  _ensure_project_skill_dir "$project" agents && agents_active=1
  _ensure_project_skill_dir "$project" claude && claude_active=1
  _ensure_project_skill_dir "$project" codex && codex_active=1
  _ensure_project_metadata_dir "$project" && manifest_active=1

  echo "==> Beislið project install ($project)"
  echo "mode: $PROJECT_MODE"
  echo "source: $SCRIPT_DIR"
  echo

  if [[ ! -f "$project/.beislid/workflow.md" ]]; then
    echo "note: .beislid/workflow.md not found in $project; project install does not create workflow config. Run the agent setup workflow when you need repo-aware workflows." >&2
  fi

  echo "Skills:"
  PROJECT_INSTALLED_LINKS=0
  PROJECT_SKIPPED_LINKS=0
  PROJECT_INSTALLED_COPIES=0
  PROJECT_REFRESHED_COPIES=0
  PROJECT_SKIPPED_COPIES=0
  PROJECT_OWNED_AGENTS=""
  PROJECT_OWNED_CLAUDE=""
  PROJECT_OWNED_CODEX=""
  PROJECT_FINGERPRINT_AGENTS=""
  PROJECT_FINGERPRINT_CLAUDE=""
  PROJECT_FINGERPRINT_CODEX=""
  local skill_dir name src
  for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    [[ -d "$skill_dir" ]] || continue
    name="$(basename "$skill_dir")"
    src="$SCRIPT_DIR/skills/$name"
    if [[ "$agents_active" == 1 ]]; then
      if [[ "$PROJECT_MODE" == "copy" ]]; then
        _project_copy_and_count "$project" agents "$src" "$agents_dir/$name" "$name (agents)" "$name"
      else
        _project_link_and_count "$src" "$agents_dir/$name" "$name (agents)"
      fi
    elif [[ "$PROJECT_MODE" == "copy" ]]; then
      PROJECT_SKIPPED_COPIES=$((PROJECT_SKIPPED_COPIES + 1))
    else
      PROJECT_SKIPPED_LINKS=$((PROJECT_SKIPPED_LINKS + 1))
    fi
    if [[ "$claude_active" == 1 ]]; then
      if [[ "$PROJECT_MODE" == "copy" ]]; then
        _project_copy_and_count "$project" claude "$src" "$claude_dir/$name" "$name (claude)" "$name"
      else
        _project_link_and_count "$src" "$claude_dir/$name" "$name (claude)"
      fi
    elif [[ "$PROJECT_MODE" == "copy" ]]; then
      PROJECT_SKIPPED_COPIES=$((PROJECT_SKIPPED_COPIES + 1))
    else
      PROJECT_SKIPPED_LINKS=$((PROJECT_SKIPPED_LINKS + 1))
    fi
    if [[ "$codex_active" == 1 ]]; then
      if [[ "$PROJECT_MODE" == "copy" ]]; then
        _project_copy_and_count "$project" codex "$src" "$codex_dir/$name" "$name (codex)" "$name"
      else
        _project_link_and_count "$src" "$codex_dir/$name" "$name (codex)"
      fi
    elif [[ "$PROJECT_MODE" == "copy" ]]; then
      PROJECT_SKIPPED_COPIES=$((PROJECT_SKIPPED_COPIES + 1))
    else
      PROJECT_SKIPPED_LINKS=$((PROJECT_SKIPPED_LINKS + 1))
    fi
  done

  if [[ "$manifest_active" == 1 ]]; then
    _write_project_manifest "$project" "$agents_dir" "$claude_dir" "$codex_dir" "$PROJECT_MODE" "$PROJECT_INSTALLED_LINKS" "$PROJECT_SKIPPED_LINKS" "$PROJECT_INSTALLED_COPIES" "$PROJECT_REFRESHED_COPIES" "$PROJECT_SKIPPED_COPIES"
  fi

  _project_gitignore_guidance "$project"

  echo
  echo "Done. Restart Claude Code / pi / Codex from this project to pick up project-local skills."
}

_count_project_installed_skills() {
  local project="$1"
  local count=0 dir skill_dir skill expected host found
  for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill="$(basename "$skill_dir")"
    expected="$SCRIPT_DIR/skills/$skill"
    found=0
    for host in agents claude codex; do
      case "$host" in
        agents) dir="$project/.agents/skills" ;;
        claude) dir="$project/.claude/skills" ;;
        codex) dir="$project/.codex/skills" ;;
      esac
      if [[ -L "$dir/$skill" && "$(readlink "$dir/$skill")" == "$expected" ]]; then
        found=1
        break
      fi
      if [[ -d "$dir/$skill" ]] && _project_copy_is_owned "$project" "$host" "$skill" "$dir/$skill"; then
        found=1
        break
      fi
    done
    if [[ "$found" == 1 ]]; then
      count=$((count + 1))
    fi
  done
  printf '%s\n' "$count"
}

beislid_status_project() {
  local requested="${1:-}"
  local project
  if ! project="$(_project_target_from_arg "$requested")"; then
    return 1
  fi

  local manifest="$(_project_manifest_path "$project")"
  echo "beislid project status"
  echo "  project: $project"
  if [[ -f "$manifest" ]]; then
    echo "  manifest: $manifest"
    if command -v python3 >/dev/null 2>&1; then
      python3 - <<'PY' "$manifest"
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print("  manifest_detail: unreadable")
    sys.exit(0)
print(f"  mode: {data.get('mode', 'unknown')}")
print(f"  source_path: {data.get('source_path', 'unknown')}")
PY
    else
      echo "  manifest_detail: present but python3 is unavailable"
    fi
  else
    echo "  manifest: missing ($manifest)"
  fi

  local name dir state count
  for name in agents claude codex; do
    case "$name" in
      agents) dir="$project/.agents/skills" ;;
      claude) dir="$project/.claude/skills" ;;
      codex) dir="$project/.codex/skills" ;;
    esac
    if [[ -d "$dir" ]]; then
      state="present"
    else
      state="missing"
    fi
    echo "  $name: $state ($dir)"
  done

  count="$(_count_project_installed_skills "$project")"
  echo "  installed_skills: $count"
}

_preserve_manifest_for_update() {
  if [[ ! -f "$MANIFEST" ]]; then
    echo "info: no existing install manifest found; update will use explicitly supplied flags only"
    return
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    echo "warn: python3 not found; cannot read install manifest" >&2
    return
  fi

  local manifest_values security manifest_claude manifest_agents manifest_codex manifest_hooks manifest_bin_dir
  manifest_values="$(python3 - <<'PY' "$MANIFEST"
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    data = {}
skill_dirs = data.get("skill_dirs") or {}
print("1" if data.get("security_hooks") is True else "0")
print(skill_dirs.get("claude") or "")
print(skill_dirs.get("agents") or "")
print(skill_dirs.get("codex") or "")
print(data.get("hooks_dir") or "")
print(data.get("bin_dir") or "")
PY
)"
  security="$(sed -n '1p' <<<"$manifest_values")"
  manifest_claude="$(sed -n '2p' <<<"$manifest_values")"
  manifest_agents="$(sed -n '3p' <<<"$manifest_values")"
  manifest_codex="$(sed -n '4p' <<<"$manifest_values")"
  manifest_hooks="$(sed -n '5p' <<<"$manifest_values")"
  manifest_bin_dir="$(sed -n '6p' <<<"$manifest_values")"

  if [[ "$security" == "1" && "$WITH_SECURITY_HOOKS" == 0 ]]; then
    WITH_SECURITY_HOOKS=1
    echo "preserve: security hooks enabled from install manifest"
  fi
  if [[ -z "${CLAUDE_SKILLS_DIR+x}" && -n "$manifest_claude" ]]; then
    CLAUDE_SKILLS="$manifest_claude"
    echo "preserve: Claude skills dir from install manifest"
  fi
  if [[ -z "${AGENTS_SKILLS_DIR+x}" && -n "$manifest_agents" ]]; then
    AGENTS_SKILLS="$manifest_agents"
    echo "preserve: agents skills dir from install manifest"
  fi
  if [[ -z "${CODEX_SKILLS_DIR+x}" && -n "$manifest_codex" ]]; then
    CODEX_SKILLS="$manifest_codex"
    echo "preserve: Codex skills dir from install manifest"
  fi
  if [[ -z "${CLAUDE_HOOKS_DIR+x}" && -n "$manifest_hooks" ]]; then
    CLAUDE_HOOKS="$manifest_hooks"
    echo "preserve: Claude hooks dir from install manifest"
  fi
  if [[ -z "${BEISLID_BIN_DIR+x}" && -n "$manifest_bin_dir" ]]; then
    BEISLID_BIN_DIR_RESOLVED="$manifest_bin_dir"
    BEISLID_CLI_PATH="$BEISLID_BIN_DIR_RESOLVED/beislid"
    echo "preserve: bin dir from install manifest"
  fi
}

_manifest_bool_is_true() {
  case "${1:-}" in
    True|true|1|yes) return 0 ;;
    *) return 1 ;;
  esac
}

_manifest_version_is_pre_v0_2() {
  local version="${1:-}"
  python3 - <<'PY' "$version"
import re, sys
version = (sys.argv[1] or "").strip().lstrip("v")
if not version or version == "unknown":
    sys.exit(0)
parts = [int(p) for p in re.findall(r"\d+", version)[:3]]
while len(parts) < 3:
    parts.append(0)
sys.exit(0 if tuple(parts) < (0, 2, 0) else 1)
PY
}

_manifest_snapshot_lines() {
  if [[ ! -f "$MANIFEST" ]]; then
    return 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    return 1
  fi
  python3 - <<'PY' "$MANIFEST"
import json, os, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    data = {}
skill_dirs = data.get("skill_dirs") or {}
cli_path = data.get("cli_path") or ""
bin_dir = data.get("bin_dir") or (os.path.dirname(cli_path) if cli_path else "")
values = {
    "repo": data.get("repo") or "",
    "version": data.get("version") or "unknown",
    "claude": skill_dirs.get("claude") or "",
    "agents": skill_dirs.get("agents") or "",
    "codex": skill_dirs.get("codex") or "",
    "hooks": data.get("hooks_dir") or "",
    "bin_dir": bin_dir,
    "cli_path": cli_path,
    "security_hooks": "True" if data.get("security_hooks") is True else "False",
}
for key in ("repo", "version", "claude", "agents", "codex", "hooks", "bin_dir", "cli_path", "security_hooks"):
    print(values[key])
PY
}

_symlink_target_abs() {
  local link="$1" target dir
  target="$(readlink "$link")" || return 1
  case "$target" in
    /*) printf '%s\n' "$target" ;;
    *)
      dir="$(cd -P "$(dirname "$link")" && pwd)"
      printf '%s/%s\n' "$dir" "$target"
      ;;
  esac
}

_path_is_same_or_under() {
  local path="$1" root="$2"
  [[ -n "$path" && -n "$root" ]] || return 1
  case "$path" in
    "$root"|"$root"/*) return 0 ;;
    *) return 1 ;;
  esac
}

_migrate_remove_symlink_if_under() {
  local link="$1" root="$2" label="$3" target
  [[ -L "$link" && -n "$root" ]] || return 0
  target="$(_symlink_target_abs "$link")" || return 0
  if _path_is_same_or_under "$target" "$root"; then
    rm "$link"
    echo "migrate: removed old $label link $link -> $target"
    BEISLID_MIGRATION_REMOVED=$((BEISLID_MIGRATION_REMOVED + 1))
  fi
}

_migrate_cleanup_links_in_dir() {
  local dir="$1" root="$2" label="$3" link
  [[ -d "$dir" && -n "$root" ]] || return 0
  local old_nullglob
  old_nullglob="$(shopt -p nullglob || true)"
  shopt -s nullglob
  for link in "$dir"/*; do
    _migrate_remove_symlink_if_under "$link" "$root" "$label"
  done
  eval "$old_nullglob"
}

beislid_migrate_v0_2() {
  echo "Migration v0.2:"
  if [[ ! -f "$MANIFEST" ]]; then
    echo "manifest: missing ($MANIFEST)"
    echo "info: no previous install manifest found; running a normal user install"
    echo
    beislid_install_user
    return
  fi

  local snapshot old_repo old_version old_claude old_agents old_codex old_hooks old_bin_dir old_cli_path old_security
  if ! snapshot="$(_manifest_snapshot_lines)"; then
    echo "warn: could not read previous install manifest; running a normal user install" >&2
    echo
    beislid_install_user
    return
  fi
  old_repo="$(sed -n '1p' <<<"$snapshot")"
  old_version="$(sed -n '2p' <<<"$snapshot")"
  old_claude="$(sed -n '3p' <<<"$snapshot")"
  old_agents="$(sed -n '4p' <<<"$snapshot")"
  old_codex="$(sed -n '5p' <<<"$snapshot")"
  old_hooks="$(sed -n '6p' <<<"$snapshot")"
  old_bin_dir="$(sed -n '7p' <<<"$snapshot")"
  old_cli_path="$(sed -n '8p' <<<"$snapshot")"
  old_security="$(sed -n '9p' <<<"$snapshot")"

  echo "manifest: $MANIFEST"
  echo "previous_repo: ${old_repo:-unknown}"
  echo "previous_version: ${old_version:-unknown}"

  if _manifest_bool_is_true "$old_security" && [[ "$WITH_SECURITY_HOOKS" == 0 ]]; then
    WITH_SECURITY_HOOKS=1
    echo "preserve: security hooks enabled from install manifest"
  fi
  if [[ -z "${CLAUDE_SKILLS_DIR+x}" && -n "$old_claude" ]]; then
    CLAUDE_SKILLS="$old_claude"
    echo "preserve: Claude skills dir from install manifest"
  fi
  if [[ -z "${AGENTS_SKILLS_DIR+x}" && -n "$old_agents" ]]; then
    AGENTS_SKILLS="$old_agents"
    echo "preserve: agents skills dir from install manifest"
  fi
  if [[ -z "${CODEX_SKILLS_DIR+x}" && -n "$old_codex" ]]; then
    CODEX_SKILLS="$old_codex"
    echo "preserve: Codex skills dir from install manifest"
  fi
  if [[ -z "${CLAUDE_HOOKS_DIR+x}" && -n "$old_hooks" ]]; then
    CLAUDE_HOOKS="$old_hooks"
    echo "preserve: Claude hooks dir from install manifest"
  fi
  if [[ -z "${BEISLID_BIN_DIR+x}" && -n "$old_bin_dir" ]]; then
    BEISLID_BIN_DIR_RESOLVED="$old_bin_dir"
    BEISLID_CLI_PATH="$BEISLID_BIN_DIR_RESOLVED/beislid"
    echo "preserve: bin dir from install manifest"
  fi

  BEISLID_MIGRATION_REMOVED=0
  if [[ -n "$old_repo" ]]; then
    _migrate_cleanup_links_in_dir "$old_claude" "$old_repo/skills" "skill"
    _migrate_cleanup_links_in_dir "$old_agents" "$old_repo/skills" "skill"
    _migrate_cleanup_links_in_dir "$old_codex" "$old_repo/skills" "skill"
    _migrate_cleanup_links_in_dir "$CLAUDE_SKILLS" "$old_repo/skills" "skill"
    _migrate_cleanup_links_in_dir "$AGENTS_SKILLS" "$old_repo/skills" "skill"
    _migrate_cleanup_links_in_dir "$CODEX_SKILLS" "$old_repo/skills" "skill"
    _migrate_cleanup_links_in_dir "$old_hooks" "$old_repo/hooks" "hook"
    _migrate_cleanup_links_in_dir "$CLAUDE_HOOKS" "$old_repo/hooks" "hook"
    _migrate_remove_symlink_if_under "$old_cli_path" "$old_repo/bin" "CLI"
    _migrate_remove_symlink_if_under "$BEISLID_CLI_PATH" "$old_repo/bin" "CLI"
  fi
  echo "cleanup: removed $BEISLID_MIGRATION_REMOVED old Beislið symlink(s)"

  if _manifest_version_is_pre_v0_2 "$old_version"; then
    echo "note: v0.2 uses clean repository history; keep or remove the old checkout manually after confirming this install."
  else
    echo "note: previous manifest is already v0.2+; refreshed install targets anyway."
  fi
  echo
  beislid_install_user
}

beislid_update_repo() {
  if ! git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "error: --update must be run from a git checkout of Beislið" >&2
    exit 1
  fi

  if [[ -n "$(git -C "$SCRIPT_DIR" status --porcelain --untracked-files=all)" ]]; then
    echo "error: cannot update with uncommitted local changes in $SCRIPT_DIR" >&2
    echo "       Commit, stash, or discard them, then re-run './install.sh --update' or 'beislid update'." >&2
    git -C "$SCRIPT_DIR" status --short >&2
    exit 1
  fi

  echo "Update:"
  _preserve_manifest_for_update
  echo "pull: git -C $SCRIPT_DIR pull --ff-only"
  git -C "$SCRIPT_DIR" pull --ff-only

  local rerun_args=()
  [[ "$WITH_SECURITY_HOOKS" == 1 ]] && rerun_args+=(--with-security-hooks)
  [[ "$FORCE" == 1 ]] && rerun_args+=(--force)

  local rerun_display=""
  if (( ${#rerun_args[@]} > 0 )); then
    rerun_display=" ${rerun_args[*]}"
  fi

  echo
  echo "restart: $SCRIPT_DIR/install.sh$rerun_display"
  if (( ${#rerun_args[@]} > 0 )); then
    exec env \
      CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
      AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
      CODEX_SKILLS_DIR="$CODEX_SKILLS" \
      CLAUDE_HOOKS_DIR="$CLAUDE_HOOKS" \
      BEISLID_BIN_DIR="$BEISLID_BIN_DIR_RESOLVED" \
      "$SCRIPT_DIR/install.sh" "${rerun_args[@]}"
  else
    exec env \
      CLAUDE_SKILLS_DIR="$CLAUDE_SKILLS" \
      AGENTS_SKILLS_DIR="$AGENTS_SKILLS" \
      CODEX_SKILLS_DIR="$CODEX_SKILLS" \
      CLAUDE_HOOKS_DIR="$CLAUDE_HOOKS" \
      BEISLID_BIN_DIR="$BEISLID_BIN_DIR_RESOLVED" \
      "$SCRIPT_DIR/install.sh"
  fi
}

beislid_install_user() {
  mkdir -p "$CLAUDE_SKILLS"
  mkdir -p "$AGENTS_SKILLS"
  mkdir -p "$CODEX_SKILLS"

  echo "==> Beislið install ($SCRIPT_DIR)"
  echo

  echo "Skills:"
  cleanup_legacy_skills
  local skill_dir name
  for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    [[ -d "$skill_dir" ]] || continue
    name="$(basename "$skill_dir")"
    link_skill "$name"
  done

  if [[ "$WITH_SECURITY_HOOKS" == 1 ]]; then
    if ! command -v python3 >/dev/null 2>&1; then
      echo "error: --with-security-hooks requires python3 on PATH" >&2
      exit 1
    fi
    echo
    echo "Security hooks:"
    link_hook "credential_guard.py"
    link_hook "credential_guard.json"
    echo
    echo "NOTE: you still need to register the hook in settings.json."
    echo "See docs/credential-guard.md for the snippet."
  fi

  echo
  echo "CLI:"
  install_cli_link

  _write_manifest

  echo
  echo "Done. Restart Claude Code / pi / Codex to pick up new skills."
}
