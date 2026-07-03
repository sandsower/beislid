# BEI-131 Canonical Parser Decisions (HITL session 2026-07-03)

Status: **approved by Vic 2026-07-03**.
Ticket: BEI-131 (P1a fix-forward conformance spec, teotl unification program).
Scope: the ~10 canonical behavior decisions for the deterministic trio parser surface (workflow_normalizer primary; error-code catalog spans workflow_normalizer, action_policy, validate_export).
Every "current behavior" below was reproduced live against `scripts/workflow_normalizer.py` on main before deciding.

These decisions are the contract.
The golden corpus encodes them; olin (OLI-13 onward) ports against the corpus, not against the Python implementations.

## Decisions

### D1 (B1) - Trailing comments in values: YAML semantics

In an unquoted scalar value, a `#` preceded by whitespace starts a comment; the value ends before it.
Quoted values keep `#` literally.
A literal ` # ` inside a command requires quoting the value.

- `parallel_safe: true # optional` -> `true` (boolean)
- `autofix: npm run lint -- --fix # optional` -> `npm run lint -- --fix`
- `command: 'echo "a # b"'` -> `echo "a # b"`

Consequence: the format doc's gate examples (`workflow-md-format.md:408-409`) become correct as written; no doc amendment needed for B1.

### D2 (B2) - Inline flow maps: rejected with explicit error

`- { name: lint, command: 'pnpm lint' }` is a parse error (`flow_map_unsupported`), never a silent literal string.
Block style is the one canonical way to write a mapping.
Doc amendment required: the two flow-map examples in the scopes section (`workflow-md-format.md:676,695`) rewrite to block style.

### D3 (B4) - Error line numbers: absolute workflow.md lines

Parse diagnostics report the physical line number in workflow.md (fence start offset threaded into the parser), not an index into a comment/blank-stripped array.
This matches the existing `duplicate_key` fence diagnostic, which already computes absolute lines.

### D4 (B5) - Unknown `beislid:<key>` fences: warning against the full documented registry

The normalizer carries the complete documented fence-key registry (all fence keys defined in `workflow-md-format.md`, roughly 22, not just the 7 in `TARGET_KEYS`).
Any `beislid:*` fence whose key is not in the registry produces an `unknown_fence_key` warning with the absolute line number (status `warning`, exit 0).
Registered-but-not-consumed keys (scopes, babysit, action_policy, ...) stay silent for the normalizer; they belong to other tools.
Forward compatibility: a newer fence key against an older normalizer degrades to a warning, never a hard failure.
The registry must be derived from the format doc during corpus encoding and kept in sync (consistency check welcome).

### D5 (B8) - Tier enums: validated in the normalizer, error severity

`tiers` keys must be exactly `light`, `standard`, `heavy`, `frontier`; `tier_mode` must be `prefer` or `require`.
Violations are `invalid_value` errors at normalize time, same as `clean_eval.mode` and `visual_surfaces.mode` today.
`validate_export` keeps its downstream enforcement; the normalizer simply fails first.

### D6 - `model` + `models` both present: error

Doc already says "use one or the other, not both".
Both present on one route is an `invalid_value` error on that route path.
No silent winner.

### D7 (B13) - Floats: parsed as numbers

`-?\d+\.\d+` parses as a JSON number, consistent with the existing int rule.
Not floats: exponents, `1.`, `.5`, `1.5.2` (all stay strings).

### D8 (B13) - Nested inline lists: error

A `[` inside an inline list is a `nested_inline_list` parse error pointing at block style.
The inline-list grammar stays flat and trivially portable.

### D9 (B13) - Quote semantics: YAML-lite

Double-quoted scalars process exactly this escape set: `\n`, `\t`, `\\`, `\"`.
Any other escape in a double-quoted scalar is an `unknown_escape` error.
Single-quoted scalars are literal except `''` -> `'`.

- `"line1\nline2"` -> `line1<newline>line2`
- `'don''t'` -> `don't`
- `'a\nb'` -> `a\nb` (literal)

### D10 - Duplicate `beislid:<key>` fences: keep warn + first wins

Current behavior is canon: `duplicate_key` warning with absolute line, first occurrence wins.
The corpus pins it.

### D11 - Stable error codes: extend the snake_case set

Keep the existing code style and freeze the catalog once shipped.
Catalog (severity as decided above):

| code | severity |
|------|----------|
| `workflow_not_found` | error |
| `invalid_version_stamp` | error |
| `malformed_block` | error |
| `invalid_section_shape` | error |
| `invalid_value` | error |
| `unknown_gate_set` | error |
| `flow_map_unsupported` | error (new) |
| `nested_inline_list` | error (new) |
| `unknown_escape` | error (new) |
| `unknown_fence_key` | warning (new) |
| `duplicate_key` | warning |
| `reserved_value` | warning |
| `reserved_field` | warning |

Corpus encoding must also catalog action_policy and validate_export codes into the same document so the trio ships one error-code contract.

### D12 - Golden corpus shape: input + expected-envelope pairs

`tests/conformance/cases/<case-name>/` holding a full `workflow.md` input and `expected.json` (the complete normalized envelope including diagnostics).
A small `run_conformance.py` runner diffs actual vs expected and runs in CI against the Python trio now; olin later runs the identical case directories.
Language-neutral by construction.

## Open encoding details (defaults proposed, confirm at corpus review)

- Unterminated/mismatched quote on a scalar (e.g. `name: "abc`): propose `unknown_escape`-style hard error (`unterminated_quote`) for consistency with the inline-list rule that already errors; today it silently stays a literal string.
- Whether ` #` comment stripping applies inside inline lists between elements: propose yes, same rule everywhere outside quotes.

## Consequences and next steps

1. Encode D1-D12 as the golden corpus + error-code catalog (AFK-able; covers workflow_normalizer, action_policy, validate_export; the trio currently has 6 normalizer tests and zero parser edge cases).
2. Amend `workflow-md-format.md` scopes examples (D2) and add the quote/float/comment rules to the format doc so doc and implementation agree.
3. Ship behavior deltas as a beislid release with release notes documenting every delta (B1/B2/B4/B5/B8/B13 changes are all behavior changes).
4. OLI-13 onward ports against `tests/conformance/cases/`, unblocking once this ships.
