#!/usr/bin/env bash
# Bump the package version in both package.json and .claude-plugin/plugin.json
# together. Prints the new version on stdout; human messages go to stderr.
#
# Usage:
#   scripts/bump-version.sh patch
#   scripts/bump-version.sh minor
#   scripts/bump-version.sh major
#   scripts/bump-version.sh 1.2.3
#
# Refuses to bump if the two files are out of sync. Fix manually first.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PKG="$REPO_ROOT/package.json"
PLUGIN="$REPO_ROOT/.claude-plugin/plugin.json"

bump_kind="${1:-}"
if [[ -z "$bump_kind" ]]; then
  echo "usage: $0 <patch|minor|major|x.y.z>" >&2
  exit 2
fi

_read_version() {
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$1"
}

_write_version() {
  python3 - "$1" "$2" <<'PY'
import json, sys
path, new = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
data["version"] = new
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
}

pkg_v=$(_read_version "$PKG")
plugin_v=$(_read_version "$PLUGIN")

if [[ "$pkg_v" != "$plugin_v" ]]; then
  echo "version drift: package.json=$pkg_v plugin.json=$plugin_v" >&2
  echo "fix manually before bumping" >&2
  exit 1
fi

current="$pkg_v"
semver_re='^([0-9]+)\.([0-9]+)\.([0-9]+)$'
if [[ ! "$current" =~ $semver_re ]]; then
  echo "current version is not semver: $current" >&2
  exit 1
fi
maj="${BASH_REMATCH[1]}"
min="${BASH_REMATCH[2]}"
pat="${BASH_REMATCH[3]}"

case "$bump_kind" in
  patch) new="$maj.$min.$((pat + 1))" ;;
  minor) new="$maj.$((min + 1)).0" ;;
  major) new="$((maj + 1)).0.0" ;;
  *)
    if [[ "$bump_kind" =~ $semver_re ]]; then
      new="$bump_kind"
    else
      echo "invalid bump: $bump_kind (use patch|minor|major|x.y.z)" >&2
      exit 2
    fi
    ;;
esac

_write_version "$PKG" "$new"
_write_version "$PLUGIN" "$new"

echo "bumped: $current -> $new" >&2
echo "$new"
