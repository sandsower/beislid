# kickoff step 3 team guidance v1

Authoritative JIT protocol for kickoff Step 3. Load after codebase context is gathered.

## Purpose

Fold optional local team guidance into downstream routing and blueprint context.

## Protocol

Print the Step 3 entry one-liner from `kickoff-templates.md`.

This is an inline file check, not a workflow capability and not a probe-cache entry.

Read `${BEISLID_CONFIG_DIR:-$HOME/.config/beislid}/team-config.md` if it exists. Otherwise fall back to `~/.claude/team-config.md` if present.

If the file has an `Enabled: true` section, note team-specific routing, review, QA, or delegation rules so blueprint can fold them into the plan. Otherwise skip.

## Exit

Print the Step 3 exit one-liner. Required outputs: `team_config_status` (`found`, `disabled`, or `not configured`) and any constraints relevant to spec/blueprint/implementation.

## Tripwires

- Missing team config is normal and must not block kickoff.
- Do not treat team config as workflow.md capability state.
