#!/usr/bin/env bash
# Tests for scripts/validate_export.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VALIDATOR="$REPO_DIR/scripts/validate_export.py"
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

# Build a valid approved-slice-plan-export-v0 bundle at $1.
write_valid_bundle() {
  python3 - "$1" <<'PY'
import json, os, sys

bundle_dir = sys.argv[1]
slices_dir = os.path.join(bundle_dir, "slices")
os.makedirs(slices_dir, exist_ok=True)

bundle = {
    "kind": "approved-slice-plan-export-v0",
    "version": 1,
    "status": "approved",
    "supersedes": None,
    "generated_from": "BEI-999",
    "source_work_contract": {"title": "Fixture contract", "status": "approved"},
    "slice_plan": {"id": "fixture-plan"},
    "children": [{"id": "slice-a"}, {"id": "slice-b"}],
    "dependency_graph": {"slice-a": [], "slice-b": ["slice-a"]},
    "proof_requirements": [],
    "guides_and_gates": {"selected_gates": [], "guides": []},
    "approval": {"approved_at": "2026-06-11T00:00:00Z", "approved_by": "Fixture Human"},
    "runner_extensions": {},
    "validation": {
        "schema_version": "approved-slice-plan-export-v0",
        "rubric_version": "afk-rubric-v0",
        "notes": "",
    },
    "ownership": {"beislid": "planning", "rondo": "execution"},
}

with open(os.path.join(bundle_dir, "bundle.json"), "w", encoding="utf-8") as fh:
    json.dump(bundle, fh, indent=2)

for slice_id in ("slice-a", "slice-b"):
    manifest = {
        "schema": "approved-slice-v1",
        "slice_id": slice_id,
        "prompt": f"Implement {slice_id} per the approved plan.",
        "boundaries": ["Stay in scope."],
        "dependencies": [],
        "proof_requirements": ["run gates"],
        "output_expectations": {"final_report": True},
        "parent_contract": {"id": "fixture-plan", "source": "beislid"},
        "repo": {
            "url": "https://example.invalid/fixture.git",
            "base_ref": "main",
            "base_sha": "0" * 40,
        },
        "allowed_actions": {"run_mode": "supervised-auto", "allow": [], "ask": [], "deny": []},
        "process_provider": {"name": "claude_code"},
        "runner_extensions": {},
    }
    with open(os.path.join(slices_dir, f"{slice_id}.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    with open(os.path.join(slices_dir, f"{slice_id}.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# {slice_id}\n\nHuman-readable summary.\n")
PY
}

# Apply a python mutation snippet to the bundle.json at $1; snippet sees `bundle` dict.
mutate_bundle() {
  python3 - "$1" "$2" <<'PY'
import json, sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    bundle = json.load(fh)
exec(sys.argv[2])
with open(path, "w", encoding="utf-8") as fh:
    json.dump(bundle, fh, indent=2)
PY
}

mutate_slice() {
  python3 - "$1" "$2" <<'PY'
import json, sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    manifest = json.load(fh)
exec(sys.argv[2])
with open(path, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2)
PY
}

expect_valid() {
  local dir="$1"
  python3 "$VALIDATOR" "$dir" || { note_fail "expected exit 0"; return 1; }
}

expect_invalid() {
  local dir="$1" needle="$2" out rc=0
  out="$(python3 "$VALIDATOR" "$dir" 2>&1)" || rc=$?
  [[ "$rc" -eq 1 ]] || { note_fail "expected exit 1, got $rc: $out"; return 1; }
  grep -qiF -- "$needle" <<<"$out" || { note_fail "expected error containing '$needle', got: $out"; return 1; }
}

test_valid_bundle_passes() {
  write_valid_bundle "$TMP/bundle"
  expect_valid "$TMP/bundle"
}

test_missing_required_field() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'del bundle["ownership"]'
  expect_invalid "$TMP/bundle" "ownership"
}

test_draft_status_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["status"] = "draft"'
  expect_invalid "$TMP/bundle" "status"
}

test_unknown_kind_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["kind"] = "mystery-export-v9"'
  expect_invalid "$TMP/bundle" "kind"
}

test_cyclic_graph_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["dependency_graph"] = {"slice-a": ["slice-b"], "slice-b": ["slice-a"]}'
  expect_invalid "$TMP/bundle" "cycl"
}

test_graph_unknown_slice_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["dependency_graph"]["slice-b"] = ["slice-ghost"]'
  expect_invalid "$TMP/bundle" "slice-ghost"
}

test_missing_slice_manifest_rejected() {
  write_valid_bundle "$TMP/bundle"
  rm "$TMP/bundle/slices/slice-b.json"
  expect_invalid "$TMP/bundle" "slice-b"
}

test_missing_slice_summary_rejected() {
  write_valid_bundle "$TMP/bundle"
  rm "$TMP/bundle/slices/slice-b.md"
  expect_invalid "$TMP/bundle" "slice-b.md"
}

test_orphan_slice_rejected() {
  write_valid_bundle "$TMP/bundle"
  cp "$TMP/bundle/slices/slice-a.json" "$TMP/bundle/slices/slice-z.json"
  mutate_slice "$TMP/bundle/slices/slice-z.json" 'manifest["slice_id"] = "slice-z"'
  expect_invalid "$TMP/bundle" "slice-z"
}

test_unknown_slice_schema_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_slice "$TMP/bundle/slices/slice-a.json" 'manifest["schema"] = "unknown-v1"'
  expect_invalid "$TMP/bundle" "schema"
}

test_slice_id_mismatch_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_slice "$TMP/bundle/slices/slice-a.json" 'manifest["slice_id"] = "slice-b"'
  expect_invalid "$TMP/bundle" "slice_id"
}

test_empty_prompt_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_slice "$TMP/bundle/slices/slice-a.json" 'manifest["prompt"] = "  "'
  expect_invalid "$TMP/bundle" "prompt"
}

test_missing_repo_pin_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_slice "$TMP/bundle/slices/slice-a.json" 'del manifest["repo"]["base_sha"]'
  expect_invalid "$TMP/bundle" "base_sha"
}

test_missing_approval_fields_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'del bundle["approval"]["approved_by"]'
  expect_invalid "$TMP/bundle" "approved_by"
}

test_missing_rubric_version_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'del bundle["validation"]["rubric_version"]'
  expect_invalid "$TMP/bundle" "rubric_version"
}

test_rubric_v1_accepted() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["validation"]["rubric_version"] = "afk-rubric-v1"'
  expect_valid "$TMP/bundle"
}

test_unknown_rubric_version_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["validation"]["rubric_version"] = "afk-rubric-v99"'
  expect_invalid "$TMP/bundle" "rubric"
}

test_invalid_supersedes_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["supersedes"] = "not-a-hash"'
  expect_invalid "$TMP/bundle" "supersedes"
}

test_missing_supersedes_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'del bundle["supersedes"]'
  expect_invalid "$TMP/bundle" "supersedes"
}

test_missing_schema_version_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'del bundle["validation"]["schema_version"]'
  expect_invalid "$TMP/bundle" "schema_version"
}

test_two_cycles_both_reported() {
  write_valid_bundle "$TMP/bundle"
  cp "$TMP/bundle/slices/slice-a.json" "$TMP/bundle/slices/slice-c.json"
  mutate_slice "$TMP/bundle/slices/slice-c.json" 'manifest["slice_id"] = "slice-c"'
  cp "$TMP/bundle/slices/slice-a.md" "$TMP/bundle/slices/slice-c.md"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["children"].append({"id": "slice-c"}); bundle["dependency_graph"] = {"slice-a": ["slice-b", "slice-c"], "slice-b": ["slice-a"], "slice-c": ["slice-a"]}'
  local out rc=0
  out="$(python3 "$VALIDATOR" "$TMP/bundle" 2>&1)" || rc=$?
  [[ "$rc" -eq 1 ]] || { note_fail "expected exit 1, got $rc"; return 1; }
  local count
  count="$(grep -c "cyclic dependency" <<<"$out")"
  [[ "$count" -ge 2 ]] || { note_fail "expected >=2 cycle errors, got $count: $out"; return 1; }
}

test_duplicate_children_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["children"].append({"id": "slice-a"})'
  expect_invalid "$TMP/bundle" "duplicate"
}

test_body_alias_accepted() {
  write_valid_bundle "$TMP/bundle"
  mutate_slice "$TMP/bundle/slices/slice-a.json" 'manifest["body"] = manifest.pop("prompt")'
  expect_valid "$TMP/bundle"
}

test_rondo_request_schema_accepted() {
  write_valid_bundle "$TMP/bundle"
  mutate_slice "$TMP/bundle/slices/slice-a.json" 'manifest["schema"] = "rondo-execution-request-v1"'
  expect_valid "$TMP/bundle"
}

test_nonpositive_version_rejected() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["version"] = 0'
  expect_invalid "$TMP/bundle" "version"
}

test_invalid_json_rejected() {
  write_valid_bundle "$TMP/bundle"
  echo "{not json" > "$TMP/bundle/bundle.json"
  expect_invalid "$TMP/bundle" "json"
}

test_missing_bundle_json_rejected() {
  mkdir -p "$TMP/bundle/slices"
  expect_invalid "$TMP/bundle" "bundle.json"
}

test_validator_is_read_only() {
  write_valid_bundle "$TMP/bundle"
  local before after
  before="$(cd "$TMP/bundle" && find . -type f -exec shasum {} + | sort)"
  python3 "$VALIDATOR" "$TMP/bundle" >/dev/null
  after="$(cd "$TMP/bundle" && find . -type f -exec shasum {} + | sort)"
  [[ "$before" == "$after" ]] || { note_fail "validator mutated the bundle"; return 1; }
}

test_cli_dispatch_valid() {
  write_valid_bundle "$TMP/bundle"
  "$CLI" export validate "$TMP/bundle" || { note_fail "beislid export validate failed on valid bundle"; return 1; }
}

test_cli_dispatch_invalid() {
  write_valid_bundle "$TMP/bundle"
  mutate_bundle "$TMP/bundle/bundle.json" 'bundle["status"] = "draft"'
  local rc=0
  "$CLI" export validate "$TMP/bundle" >/dev/null 2>&1 || rc=$?
  [[ "$rc" -eq 1 ]] || { note_fail "expected exit 1 from CLI, got $rc"; return 1; }
}

run_test "valid bundle passes" test_valid_bundle_passes
run_test "missing required field rejected" test_missing_required_field
run_test "draft status rejected" test_draft_status_rejected
run_test "unknown kind rejected" test_unknown_kind_rejected
run_test "cyclic graph rejected" test_cyclic_graph_rejected
run_test "graph referencing unknown slice rejected" test_graph_unknown_slice_rejected
run_test "missing slice manifest rejected" test_missing_slice_manifest_rejected
run_test "missing slice summary rejected" test_missing_slice_summary_rejected
run_test "orphan slice rejected" test_orphan_slice_rejected
run_test "unknown slice schema rejected" test_unknown_slice_schema_rejected
run_test "slice_id mismatch rejected" test_slice_id_mismatch_rejected
run_test "empty prompt rejected" test_empty_prompt_rejected
run_test "missing repo pin rejected" test_missing_repo_pin_rejected
run_test "missing approval fields rejected" test_missing_approval_fields_rejected
run_test "missing rubric_version rejected" test_missing_rubric_version_rejected
run_test "afk-rubric-v1 accepted" test_rubric_v1_accepted
run_test "unknown rubric_version rejected" test_unknown_rubric_version_rejected
run_test "invalid supersedes rejected" test_invalid_supersedes_rejected
run_test "missing supersedes rejected" test_missing_supersedes_rejected
run_test "missing schema_version rejected" test_missing_schema_version_rejected
run_test "two cycles both reported" test_two_cycles_both_reported
run_test "duplicate children rejected" test_duplicate_children_rejected
run_test "body alias accepted" test_body_alias_accepted
run_test "rondo-execution-request-v1 accepted" test_rondo_request_schema_accepted
run_test "non-positive version rejected" test_nonpositive_version_rejected
run_test "invalid json rejected" test_invalid_json_rejected
run_test "missing bundle.json rejected" test_missing_bundle_json_rejected
run_test "validator is read-only" test_validator_is_read_only
run_test "cli dispatch valid bundle" test_cli_dispatch_valid
run_test "cli dispatch invalid bundle" test_cli_dispatch_invalid

echo
echo "pass=$pass fail=$fail"
if (( fail > 0 )); then
  echo "failed tests:" >&2
  for name in "${failures[@]}"; do
    echo "  - $name" >&2
  done
  exit 1
fi
