---
# Rondo execution profile — beislid
# Run rondo against this profile to execute Linear issues from the
# "Rondo intake — beislid" project. Adding an issue to that project is the
# explicit AFK opt-in. Envelope-driven runs use `rondo run-once --manifest`
# and override tracker polling entirely.
tracker:
  kind: linear
  api_key: "$LINEAR_API_KEY"
  project_slug: "rondo-intake-beislid-88762f06c592"
  active_states:
    - Todo
    - In Progress
    - In Review
  terminal_states:
    - Done
    - Closed
    - Cancelled
    - Canceled
    - Duplicate
polling:
  interval_ms: 30000
workspace:
  root: ~/code/rondo-workspaces
hooks:
  after_create: |
    git clone --depth 1 git@github.com:sandsower/beislid.git .
    git checkout -B rondo/{{ issue.identifier }}
  before_run: |
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      git checkout -B rondo/{{ issue.identifier }}
    fi
gates:
  - name: skill-size-budgets
    command: python3 scripts/check_skill_size_budgets.py
  - name: validate-skills
    command: python3 scripts/validate_skills.py
  - name: visual-surfaces-consistency
    command: python3 scripts/check_visual_surfaces_consistency.py
  - name: workflow-signals-consistency
    command: python3 scripts/check_workflow_signals_consistency.py
  - name: install-integration-tests
    command: bash scripts/test_install.sh
    timeout_ms: 600000
agent:
  adapter: pi
  max_concurrent_agents: 10
  max_turns: 20
claude:
  command: claude
  permission_mode: bypassPermissions
  dangerously_skip_permissions: true
  output_format: stream-json
pi:
  command: pi
  turn_timeout_ms: 3600000
  stall_timeout_ms: 300000
model_routing:
  defaults:
    tier: standard
    mode: prefer
  tiers:
    light:
      - adapter: pi
        model: openrouter/deepseek/deepseek-chat
    standard:
      - adapter: pi
        model: openai-codex/gpt-5.4-mini
      - adapter: pi
        model: openrouter/moonshotai/kimi-k2.7-code
    heavy:
      - adapter: pi
        model: openrouter/z-ai/glm-5.2
      - adapter: pi
        model: openrouter/deepseek/deepseek-v4-pro
    frontier:
      - adapter: pi
        model: openai-codex/gpt-5.5
      - adapter: pi
        model: openrouter/deepseek/deepseek-v4-pro
  step_hints:
    initial:
      stage: kickoff
      skill: kickoff
      phase: context-discovery
      tier: frontier
      mode: prefer
      rationale: kickoff and context discovery need the broadest routing before the default standard tier takes over
    steps:
      - stage: kickoff
        skill: kickoff
        phase: planning
        tier: heavy
        mode: prefer
        rationale: planning and scope shaping benefit from heavier reasoning
      - stage: implement
        skill: implement
        tier: standard
        mode: prefer
        rationale: ordinary coding should stay on the repo default
      - stage: ready-for-review
        skill: ready-for-review
        phase: gates
        tier: standard
        mode: prefer
        rationale: gate execution is mechanical and should stay on the repo default standard tier
      - stage: review-response
        skill: review-response
        phase: fix
        tier: standard
        mode: prefer
        rationale: fixes and replies should remain on the broad repo default
    phases:
      - stage: kickoff
        skill: kickoff
        phase: context-discovery
        tier: frontier
        mode: prefer
        rationale: the initial kickoff phase should outrun the repo default standard tier
      - stage: ready-for-review
        skill: ready-for-review
        phase: review
        step: fresh-eyes
        tier: heavy
        mode: prefer
        rationale: the final review synthesis needs stronger reasoning
action_policy:
  command: beislid
  run_mode: unattended-auto
  policy_file: /Users/vicvalenzuela/Projects/beislid/.beislid/action-policy.json
process_provider:
  kind: beislid
  required: false
---

You are working on Linear ticket `{{ issue.identifier }}` in the beislid repo
(Beislið — markdown skill distribution; planning/proof/envelope semantics).

Issue context:
Identifier: {{ issue.identifier }}
Title: {{ issue.title }}
Current status: {{ issue.state }}
URL: {{ issue.url }}

Description:
{% if issue.description %}
{{ issue.description }}
{% else %}
No description provided.
{% endif %}

Instructions:

Model routing posture: this workflow intentionally dogfoods the `pi` adapter and
provider-prefixed model routing instead of Claude model aliases. Keep unattended
runs on real non-Claude routes unless a ticket explicitly requires otherwise:
default work uses GPT through the Pi subscription (`openai-codex/...`), while
Kimi, GLM, and DeepSeek coverage runs through OpenRouter (`openrouter/...`). Do
not replace these with `opus`/`sonnet`/`haiku` aliases when tuning this workflow.

1. This is an unattended orchestration session. Never ask a human to perform
   follow-up actions; only stop for a true blocker (missing auth/permissions).
2. Work only in the provided repository copy.
3. Maintain a single persistent Linear workpad comment as the source of truth
   for progress; bring it up to date before new implementation work.
4. Treat any ticket-authored Validation/Test Plan section as non-negotiable
   acceptance input; execute it before considering the work complete.
5. Project conventions live in `.beislid/workflow.md` (gates, action policy,
   ticket/PR conventions). Run the configured gates before any push.
6. Out-of-scope discoveries become new Linear issues in the same project,
   linked `related`, never scope expansion.
7. Final response must be only a valid `rondo.final_report/v0` JSON object with required fields `schema`, `summary`, `changed_files`, `gates_run`, `failures`, `risks`, and `next_state`. Use `schema: "rondo.final_report/v0"`; do not use legacy keys such as `version`, `ticket`, `completed_actions`, or `blockers` instead of the required fields.

## In Review babysit loop

When the ticket status is `In Review`, do not start new feature work. Treat the run as a review/babysit loop:

1. Find the linked/open PR for the issue branch; if none exists, move the ticket back to `In Progress`, update the workpad with the missing review artifact, and stop.
2. Read top-level PR comments, inline review comments, reviews, CI/check status, mergeability, and branch freshness.
3. Treat every actionable human/bot comment as blocking until it is fixed and replied to, or an explicit justified pushback is posted.
4. Run the configured workflow gates before every babysit-owned push or merge boundary.
5. Only leave the ticket in `In Review` when the PR is reviewable, checks are green or legitimately pending human review, and unresolved actionable feedback is recorded in the workpad. If changes are required, move the ticket to `In Progress` and execute the fixes end-to-end.
6. Never trigger AgenticReviewer on WIP/routine iteration. Request the configured provider only for final high-risk review by applying the configured opt-in label or approved PR body keyword.
