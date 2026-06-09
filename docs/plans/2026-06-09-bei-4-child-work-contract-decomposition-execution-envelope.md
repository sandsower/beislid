# BEI-4 Child Work Contract Decomposition — Execution Envelope

```yaml
kind: execution-envelope-v0
status: approved
source:
  type: linear_issue
  id: BEI-58
  title: "[Envelope] Create execution envelope for BEI-4 child Work Contract decomposition"
  related:
    - type: linear_issue
      id: BEI-4
      title: "[GH #58] [P0] Extend break-spec into child Work Contract decomposition"
    - type: github_issue
      repository: sandsower/beislid
      id: 58
      title: "[P0] Extend break-spec into child Work Contract decomposition"
    - type: linear_issue
      id: BEI-56
      title: "[Envelope] Define execution-envelope-v0 contract fixture"
  upstream_dependencies:
    - Work Contract v1
    - Scope classifier
    - Proof Requirement schema
objective: >-
  Implement BEI-4 as a repo-owned Beislið planning-semantics change that extends
  break-spec from prose phase decomposition into approved, reviewable child Work
  Contract / Slice Plan decomposition.
slice:
  id: bei-4-child-work-contract-decomposition
  include:
    - Define child-slice-v1 and slice-plan-v1 artifact shapes.
    - Update break-spec guidance so multi-slice/project inputs produce child
      contracts or slice plans rather than prose-only phases.
    - Require parent/child references, explicit acyclic dependencies,
      parallelizable groups, proof requirements, human decisions, and execution
      recommendations.
    - Record how an approved Slice Plan is associated with the parent Work
      Contract through the reserved slice_plan and children slots.
    - Preserve Beislið ownership boundaries in docs and skill guidance.
  exclude:
    - Executing, dispatching, or scheduling child slices.
    - Requiring Rondo or reading Rondo run state.
    - Creating a Teotl runtime, parser, service, daemon, database, or durable run
      store.
    - Implementing broad workflow policy changes unrelated to child Work
      Contract / Slice Plan decomposition.
required_output:
  slice_plan_v1:
    required_fields:
      - kind
      - status
      - parent_work_contract
      - children
      - dependency_graph
      - parallel_groups
      - human_decisions
      - proof_requirements
      - approval
    dependency_rule: "Dependencies must be explicit and acyclic before approval."
    approval_rule: >-
      The complete Slice Plan must be human-approved before external execution or
      child handoff begins.
  child_slice_v1:
    required_fields:
      - id
      - title
      - goal
      - in_scope
      - out_of_scope
      - parent_ref
      - depends_on
      - parallel_group
      - proof_requirements
      - human_decisions
      - execution_recommendation
    execution_recommendation_fields:
      - mode: "AFK | HITL"
      - rationale
      - suggested_execution_envelope
      - pause_conditions
      - required_handoff_artifacts
autonomy:
  allow:
    - Edit targeted Beislið docs and skill prose needed to define and route
      child Work Contract / Slice Plan decomposition.
    - Add examples or templates that make child ids, goals, boundaries,
      dependency edges, proof requirements, human decisions, and execution
      recommendations reviewable.
    - Run configured local validation gates and inspect diffs.
    - Update the parent Work Contract semantics only as needed to explain
      slice_plan and children population for BEI-4.
  ask:
    - Change action-policy defaults, workflow config grammar, lifecycle action
      behavior, or run-ledger semantics.
    - Add machine parsers, exporters, validators, or schema enforcement beyond
      human-readable planning contract documentation.
    - Touch unrelated skills or docs outside the minimum BEI-4 surface.
    - Post external ticket/PR updates, push branches, or open PRs.
    - Broaden the Slice Plan export contract beyond the approved BEI-4
      acceptance criteria.
  deny:
    - Execute or dispatch child slices.
    - Require Rondo as part of Beislið break-spec decomposition.
    - Treat Rondo run evidence as Beislið planning state.
    - Store curated memory outside Memento-owned flows.
    - Introduce a Teotl runtime, service, parser, daemon, database, or durable
      execution store.
proof_requirements:
  - kind: proof-requirement-v1
    id: diff-whitespace
    type: command_gate
    stage: pre-pr
    status: required
    success_criteria:
      - "git diff whitespace checks pass."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: gate_envelope
      reference: "git diff --check origin/main...HEAD transcript or run-ledger gate path"
  - kind: proof-requirement-v1
    id: skill-size-budgets
    type: command_gate
    stage: pre-pr
    status: required
    success_criteria:
      - "Skill size budget validation exits successfully."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: gate_envelope
      reference: "python3 scripts/check_skill_size_budgets.py transcript or run-ledger gate path"
  - kind: proof-requirement-v1
    id: validate-skills
    type: command_gate
    stage: pre-pr
    status: required
    success_criteria:
      - "Skill frontmatter/protocol validation exits successfully."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: gate_envelope
      reference: "python3 scripts/validate_skills.py transcript or run-ledger gate path"
  - kind: proof-requirement-v1
    id: workflow-surface-consistency
    type: command_gate
    stage: pre-pr
    status: required
    success_criteria:
      - "Workflow signal and visual surface consistency checks exit successfully."
    failure_policy:
      on_missing: block
      on_failure: block
      retryable: true
    expected_artifact:
      kind: gate_envelope
      reference: "visual/workflow consistency check transcript or run-ledger gate path"
pause_conditions:
  - BEI-4 requires a concrete schema field that conflicts with Work Contract v1,
    scope classifier, or proof-requirement-v1 semantics.
  - The dependency graph cannot be represented as acyclic without changing the
    accepted product boundary.
  - Human-dependent work cannot be isolated into named decisions or HITL slices.
  - The work expands into execution, dispatch, Rondo integration, Teotl runtime,
    parser/validator, or durable run storage.
  - Required validation gates are missing or fail after a reasonable retry.
  - The missing source plan referenced by BEI-58 becomes necessary to resolve a
    product decision rather than remaining non-blocking context.
dependencies:
  - Linear BEI-4 and GitHub sandsower/beislid#58 acceptance criteria.
  - Existing Work Contract v1 documentation and reserved slice_plan / children
    extension slots.
  - Existing proof-requirement-v1 documentation.
  - Local Beislið validation scripts available from the repo root.
expected_delivery:
  summary: >-
    Describe the child Work Contract / Slice Plan decomposition contract, the
    targeted docs/skill changes, and how the parent Work Contract records the
    approved plan.
  artifacts:
    - changed_files
    - proof_results
    - open_risks_or_human_decisions
    - next_step_recommendation
  next_step: >-
    ready-for-review after required gates pass, or human follow-up if a pause
    condition triggers.
ownership:
  beislid: >-
    Owns Work Contract, child-slice, slice-plan, proof requirement, routing, and
    human approval semantics.
  rondo: >-
    Owns execution and run evidence only after a future approved handoff; BEI-4
    must not require it.
  memento: >-
    Owns durable memory and learning captured by explicit Memento workflows.
  teotl: >-
    Deferred; no runtime, service, parser, daemon, database, or durable
    execution-store responsibility in this envelope.
```

## Human Approval Notes

This envelope approves BEI-4 for an AFK implementation pass within the boundaries
above. It does not approve executing child slices or building infrastructure that
would dispatch them. If implementation discovers a need to cross an `ask` item or
hits a pause condition, stop and return to the human with the smallest concrete
decision needed to continue.
