# BEI-17 Approved Slice Plan Export — Execution Envelope

```yaml
kind: execution-envelope-v0
status: approved
source:
  type: linear_issue
  id: BEI-59
  title: "[Envelope] Create execution envelope for BEI-17 approved Slice Plan export"
  related:
    - type: linear_issue
      id: BEI-17
      title: "[GH #59] [P1] Export approved Slice Plans to external runners"
    - type: github_issue
      repository: sandsower/beislid
      id: 59
      title: "[P1] Export approved Slice Plans to external runners"
    - type: linear_issue
      id: BEI-57
      title: "[Envelope] Create execution envelope for BEI-47 external runner ProcessProvider contract"
    - type: linear_issue
      id: BEI-58
      title: "[Envelope] Create execution envelope for BEI-4 child Work Contract decomposition"
  upstream_dependencies:
    - execution-envelope-v0 fixture
    - External runner ProcessProvider boundary
    - Work Contract v1
    - child-slice-v1 and slice-plan-v1 semantics
    - Proof Requirement schema
objective: >-
  Implement BEI-17 as a repo-owned Beislið export-semantics change that lets an
  approved Slice Plan be represented as a human-readable artifact and a
  versioned machine-readable manifest for external runners without requiring any
  runner to be installed.
slice:
  id: bei-17-approved-slice-plan-export
  include:
    - Define a versioned approved Slice Plan export manifest shape.
    - Define the companion human-readable markdown export artifact expectations.
    - Preserve source Work Contract, selected child slices, dependency graph,
      parallel groups, proof requirements, human decisions, guide/gate references,
      approval metadata, and execution recommendations.
    - Allow optional runner-specific fields only as extension metadata that does
      not make Beislið depend on Rondo or any other runner.
    - Add validation and doctor guidance so invalid, unsupported, or
      unrepresentable export fields fail clearly.
    - Keep ownership boundaries explicit across Beislið, Rondo, Memento, and
      deferred Teotl responsibilities.
  exclude:
    - Executing, dispatching, scheduling, or monitoring exported slices.
    - Requiring Rondo, reading Rondo run state, or encoding Rondo-only adapter
      internals as required Beislið semantics.
    - Creating a Teotl runtime, parser service, daemon, database, durable run
      store, or proof store.
    - Implementing a broad exporter framework beyond the approved Slice Plan
      export contract.
required_output:
  approved_slice_plan_export_v0:
    required_fields:
      - kind
      - version
      - status
      - generated_from
      - source_work_contract
      - slice_plan
      - children
      - dependency_graph
      - proof_requirements
      - guides_and_gates
      - approval
      - runner_extensions
      - validation
      - ownership
    kind_value: approved-slice-plan-export-v0
    status_rule: >-
      Only approved Slice Plans may be exported for external execution. Draft,
      paused, superseded, or unapproved plans must fail validation or remain
      human-readable planning artifacts only.
    preservation_rule: >-
      Parent Work Contract references, child slice identifiers, dependency edges,
      proof requirements, human decisions, and execution recommendations must be
      preserved without requiring chat scraping or Beislið internals.
    extension_rule: >-
      Runner-specific fields must live under optional extension metadata. Unknown
      required fields, unsupported runner requirements, or fields that change
      Beislið ownership must fail clearly instead of being silently ignored.
  markdown_export:
    required_sections:
      - Source and approval
      - Work Contract summary
      - Selected Slice Plan
      - Child slices
      - Dependency graph
      - Proof requirements
      - Guides and gates
      - Runner extension metadata
      - Validation notes
      - Ownership boundary
    readability_rule: >-
      A human reviewer must be able to understand what was approved, what may be
      executed externally, what proof is required, and where a runner must stop.
autonomy:
  allow:
    - Edit targeted Beislið docs and skill prose needed to define approved Slice
      Plan export semantics and examples.
    - Add examples or templates that make manifest versioning, markdown exports,
      dependencies, proof, approvals, validation failures, and optional runner
      extension fields reviewable.
    - Run configured local validation gates and inspect diffs.
    - Reference BEI-57 and BEI-58 envelope semantics as dependencies for the
      export boundary.
  ask:
    - Add new workflow.md keys, action-policy defaults, lifecycle action behavior,
      run-ledger semantics, or doctor probe capabilities beyond guidance text.
    - Add machine parsers, exporters, validators, CLI commands, schema enforcement,
      or runtime services beyond the approved contract documentation.
    - Touch unrelated skills or docs outside the minimum BEI-17 export surface.
    - Make any runner-specific field required for Beislið correctness.
    - Post external ticket/PR updates, push branches, or open PRs.
  deny:
    - Execute or dispatch exported Slice Plans.
    - Require Rondo or any external runner for Beislið to remain useful.
    - Treat Rondo run evidence as Beislið planning state or proof storage.
    - Store curated memory outside Memento-owned flows.
    - Introduce a Teotl runtime, parser service, daemon, database, durable run
      store, or execution engine.
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
  - BEI-17 requires exporter runtime behavior, parser/validator enforcement, CLI
    commands, daemon/service work, or durable storage rather than contract docs.
  - Required manifest fields cannot preserve parent/child/proof/dependency
    information without changing Work Contract, child-slice, slice-plan, or proof
    requirement semantics.
  - Validation or doctor guidance needs new workflow config grammar or executable
    probes instead of documented expectations.
  - Runner-specific fields become required Beislið semantics or encode Rondo-only
    adapter internals.
  - The work expands into execution, dispatch, Rondo integration, Teotl runtime,
    parser/validator, or durable run storage.
  - Required validation gates are missing or fail after a reasonable retry.
  - The missing source plan referenced by BEI-59 becomes necessary to resolve a
    product decision rather than remaining non-blocking context.
dependencies:
  - Linear BEI-17 and GitHub sandsower/beislid#59 acceptance criteria.
  - Approved execution-envelope-v0 fixture and external runner ProcessProvider
    boundary from BEI-57.
  - Approved child Work Contract / Slice Plan decomposition envelope from BEI-58.
  - Existing Work Contract v1, child slice, slice plan, and proof requirement
    documentation.
  - Local Beislið validation scripts available from the repo root.
expected_delivery:
  summary: >-
    Describe the approved Slice Plan export contract, the manifest and markdown
    artifact expectations, preservation guarantees, validation/doctor guidance,
    optional runner extension boundary, and remaining risks.
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
    Owns Work Contract, child-slice, slice-plan, export manifest, markdown
    artifact, proof requirement, guide/gate, validation guidance, and ownership
    boundary semantics.
  rondo: >-
    Owns external execution, runner adapters, and run evidence only after a
    future approved handoff; BEI-17 must not require it.
  memento: >-
    Owns durable memory and learning captured by explicit Memento workflows, not
    export proof storage.
  teotl: >-
    Deferred; no runtime, service, parser, daemon, database, or durable
    execution-store responsibility in this envelope.
```

## Human Approval Notes

This envelope approves BEI-17 for an AFK implementation pass within the
boundaries above. It does not approve building exporter runtime machinery,
dispatching exported slices, or requiring an external runner. If implementation
discovers a need to cross an `ask` item or hits a pause condition, stop and return
to the human with the smallest concrete decision needed to continue.
