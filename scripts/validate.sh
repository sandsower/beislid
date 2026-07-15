#!/usr/bin/env bash
# Local mirror of the CI-blocking checks in .github/workflows/validate.yml.
#
# Runs every blocking job from that workflow, in cheap-first order, and stops
# at the first failure with a clear per-check banner. Two checks that need
# tooling this machine may not have (lychee, npm/node) are warn-skipped
# rather than failed when the tool is missing - everything else must pass
# for this script to exit 0.
#
# This is the script CONTRIBUTING.md points at: run it before opening a PR.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

skipped=()

banner() {
  echo ""
  echo "==> $1"
}

warn_skip() {
  echo "SKIP: $1" >&2
  skipped+=("$1")
}

# --- lint-skills -------------------------------------------------------
banner "lint-skills: python3 scripts/validate_skills.py"
python3 scripts/validate_skills.py

# --- skill-size-budgets --------------------------------------------------
banner "skill-size-budgets: python3 scripts/check_skill_size_budgets.py"
python3 scripts/check_skill_size_budgets.py

# --- symlink-integrity ----------------------------------------------------
banner "symlink-integrity: shared format doc symlinks"
required='skills/setup/workflow-md-format.md
skills/setup/probe-semantics.md
skills/doctor/workflow-md-format.md
skills/doctor/probe-semantics.md
skills/doctor/output-templates.md
skills/doctor/doctor-templates.md
skills/ready-for-review/workflow-md-format.md
skills/ready-for-review/probe-semantics.md
skills/ready-for-review/output-templates.md
skills/ready-for-review/ready-for-review-templates.md
skills/kickoff/workflow-md-format.md
skills/kickoff/probe-semantics.md
skills/kickoff/output-templates.md
skills/kickoff/kickoff-templates.md
skills/kickoff/action-policy-protocol.md
skills/implement/action-policy-protocol.md
skills/review-response/workflow-md-format.md
skills/review-response/probe-semantics.md
skills/review-response/output-templates.md
skills/review-response/review-response-templates.md
skills/review-response/action-policy-protocol.md
skills/ready-for-review/action-policy-protocol.md
skills/kickoff/nopal-seam-protocol.md
skills/envelope/nopal-seam-protocol.md
skills/ready-for-review/nopal-seam-protocol.md
skills/review-response/nopal-seam-protocol.md
skills/implement/nopal-seam-protocol.md
skills/babysit/nopal-seam-protocol.md
skills/retro/nopal-seam-protocol.md
skills/doctor/nopal-seam-protocol.md'

missing_or_not_symlink=$(printf '%s\n' "$required" | while read -r path; do
  [ -L "$path" ] || echo "$path"
done)
if [ -n "$missing_or_not_symlink" ]; then
  echo "Missing or non-symlink required aux files:"
  echo "$missing_or_not_symlink"
  echo ""
  echo "Re-link them as: ln -sf ../../.beislid/<name>.md skills/<skill>/<name>.md"
  exit 1
fi

stray_regular=$(find skills \( -name 'probe-semantics.md' \
                      -o -name 'workflow-md-format.md' \
                      -o -name 'output-templates.md' \
                      -o -name 'doctor-templates.md' \
                      -o -name 'ready-for-review-templates.md' \
                      -o -name 'kickoff-templates.md' \
                      -o -name 'review-response-templates.md' \
                      -o -name 'action-policy-protocol.md' \
                      -o -name 'nopal-seam-protocol.md' \) \
          | xargs -I{} sh -c '[ -L "{}" ] || echo "{}"')
if [ -n "$stray_regular" ]; then
  echo "Found per-skill aux files that should be symlinks but are regular files:"
  echo "$stray_regular"
  exit 1
fi
echo "ok: all required aux files are present symlinks"

# --- consistency-checks ---------------------------------------------------
banner "consistency-checks: doc consistency checks"
python3 scripts/check_artifact_templates_consistency.py
python3 scripts/check_contract_schema_consistency.py
python3 scripts/check_lifecycle_hooks_consistency.py
python3 scripts/check_model_routing_step_hints_consistency.py
python3 scripts/check_planning_lifecycle_consistency.py
python3 scripts/check_run_ledger_skill_examples_consistency.py
python3 scripts/check_visual_surfaces_consistency.py
python3 scripts/check_workflow_signals_consistency.py
python3 scripts/check_nopal_seam_consistency.py
python3 scripts/test_nopal_identity.py

# --- validate-exports ------------------------------------------------------
banner "validate-exports: committed export bundles"
shopt -s nullglob
bundles=(.beislid/exports/*/)
if [ ${#bundles[@]} -eq 0 ]; then
  echo "no committed bundles to validate"
else
  for bundle in "${bundles[@]}"; do
    echo "=== $bundle ==="
    python3 scripts/validate_export.py "$bundle"
  done
fi
shopt -u nullglob

# --- action-policy ----------------------------------------------------------
banner "action-policy: bash scripts/test_action_policy.sh"
bash scripts/test_action_policy.sh
banner "action-policy: bash scripts/test_action_policy_protocol.sh"
bash scripts/test_action_policy_protocol.sh

# --- release-bump -----------------------------------------------------------
banner "release-bump: bash scripts/test_bump_version.sh"
bash scripts/test_bump_version.sh

# --- run-ledger ---------------------------------------------------------
banner "run-ledger: bash scripts/test_run_ledger.sh"
bash scripts/test_run_ledger.sh
banner "gate-proof: python3 scripts/test_gate_proof.py"
python3 scripts/test_gate_proof.py

# --- script-tests ------------------------------------------------------
banner "script-tests: bash scripts/test_validate_export.sh"
bash scripts/test_validate_export.sh
banner "script-tests: bash scripts/test_validate_skills.sh"
bash scripts/test_validate_skills.sh
banner "script-tests: python3 scripts/test_workflow_normalizer.py"
python3 scripts/test_workflow_normalizer.py
banner "script-tests: python3 scripts/test_workspace_placement.py"
python3 scripts/test_workspace_placement.py
banner "script-tests: python3 scripts/test_workspace_host_conformance.py"
python3 scripts/test_workspace_host_conformance.py
banner "script-tests: python3 scripts/test_resource_resolver.py"
python3 scripts/test_resource_resolver.py
banner "script-tests: python3 scripts/test_setup_skill_routing.py"
python3 scripts/test_setup_skill_routing.py
banner "script-tests: python3 scripts/test_visual_feedback.py"
python3 scripts/test_visual_feedback.py
banner "script-tests: python3 scripts/test_agent_smoke_harness.py (self-test only, no live agents)"
python3 scripts/test_agent_smoke_harness.py

# --- show-me-tests -----------------------------------------------------
banner "show-me-tests: npm test"
if command -v npm >/dev/null 2>&1; then
  npm test
else
  warn_skip "show-me-tests (npm test): npm not found on PATH"
fi

# --- smoke-install --------------------------------------------------------
banner "smoke-install: bash scripts/test_install.sh"
bash scripts/test_install.sh

# --- check-links ------------------------------------------------------------
banner "check-links: lychee markdown link check"
if command -v lychee >/dev/null 2>&1; then
  lychee --no-progress --verbose --exclude-loopback './**/*.md'
else
  warn_skip "check-links (lychee): lychee not found on PATH - install from https://github.com/lycheeverse/lychee or brew install lychee"
fi

echo ""
echo "==> all blocking checks passed"
if [ ${#skipped[@]} -gt 0 ]; then
  echo ""
  echo "warn-skipped (tooling unavailable locally, not covered by this run):"
  for s in "${skipped[@]}"; do
    echo "  - $s"
  done
fi
