# kickoff step 5 scope v1

Authoritative JIT protocol for kickoff Step 5. Load after requirements are clear or after spec returns approved requirements.

## Purpose

Classify work with the Work Contract `scope_classification` vocabulary and route it safely.

## Protocol

Print the Step 5 entry one-liner from `kickoff-templates.md`.

Produce or confirm the canonical classifier:

```yaml
scope_classification:
  kind: atomic | single_pr | multi_slice | project | unknown
  confidence: low | medium | high
  rationale: <why this classification fits>
  recommended_route: spec_refinement | minimal_blueprint | blueprint | break_spec | project_planning
  requires_human_approval: true | false
  requires_split: true | false
  split_reason: <reason or null>
```

Classification rules:

- `atomic`: bounded, clear, low-branching work; route to `minimal_blueprint` or `blueprint`; do not over-decompose.
- `single_pr`: one coherent reviewable PR; route to `blueprint`.
- `multi_slice`: known direction with multiple independently shippable vertical slices; route to `break-spec` and require `split_reason`.
- `project`: needs milestones, contracts, or ownership boundaries before child execution; use `recommended_route: spec_refinement` while boundaries are unresolved, then `project_planning` after boundaries are approved before `break-spec`/slice planning. Do not scaffold by default.
- `unknown`: draft-only; route to `spec_refinement`, set `confidence: low`, and do not proceed to automation as approved.

Always show the classifier before using it to route downstream work. `requires_human_approval: true` means an extra approval boundary beyond normal spec/blueprint approval. Require it when classification triggers decomposition, fanout, project planning, contradicts the user's expected route, or has low confidence with high consequence. When true, stop, present the classifier and proposed route, wait for explicit approval, record approved/declined, and do not invoke downstream automation until approved. If approval is required because boundaries are broad, recommend refinement questions that could narrow the route.

Examples: typo-level doc fix with no branching → `atomic`; one coherent skill behavior update → `single_pr`; multiple shippable workflow slices → `multi_slice`; broad initiative needing milestones/boundaries → `project`.

Derived prose may still say `fits one PR` for `atomic`/`single_pr` or `needs decomposition` for `multi_slice`/`project`, but the four-way classifier is canonical.

When routing to `break-spec`, carry the approved spec/requirements or Work Contract, any spec artifact status/path returned by `spec`, ticket, context, domain notes, team constraints, and risks.

For `multi_slice` or `project` with AFK-suitable slices (clear boundaries, machine-checkable proof, low ambiguity), print the envelope suggestion one-liner from `kickoff-templates.md` after the route summary, recommending `/envelope` in a strong-model session for those slices. Recommendation only — never auto-route into or invoke `/envelope`.

## Exit

Print the Step 5 exit one-liner. Required outputs: `scope_classification`, derived route summary, rationale, spec/Work Contract artifact status/path if present, and selected phase if breakdown is invoked and a phase is chosen.

## Tripwires

- Do not let kickoff proceed to blueprint for `multi_slice` or `project` work without explicit phase/slice selection.
- Keep vertical slices shippable; do not decompose by technical layer only.
- Do not use `unknown` in an approved automation handoff.
