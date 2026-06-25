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
  max_concurrent_agents: 2
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
7. Final message reports completed actions and blockers only.
