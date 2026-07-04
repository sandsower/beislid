# Parser conformance

This repo’s parser contract is encoded as golden cases under `tests/conformance/cases/` and exercised by `scripts/run_conformance.py`.

## Corpus shape

Each case directory contains:

- `workflow.md` — complete input file
- `expected.json` — full normalized envelope

The runner masks `source.path` before diffing. `source.workflow_hash` remains part of the contract.

## Frozen diagnostic catalog

These codes are stable once shipped.

| code | severity | when emitted | path convention |
| --- | --- | --- | --- |
| `workflow_not_found` | error | workflow file cannot be read | `source.path` |
| `invalid_version_stamp` | error | first line is not `<!-- beislid-workflow: v1 -->` | `source.version_stamp` |
| `malformed_block` | error | a fence block cannot be parsed (bad structure, unterminated fence, unterminated inline list) | `sections.<key>` |
| `invalid_section_shape` | error | a target section has the wrong top-level type | `sections.<key>` |
| `invalid_value` | error | enum / route / tier validation fails | `sections.<key>...` |
| `unknown_gate_set` | error | a `gate_sets` selector references a missing set | `sections.gate_sets.selectors[n].gate_sets` |
| `flow_map_unsupported` | error | a list item uses flow-map syntax (`- { ... }`) | `sections.<key>` |
| `nested_inline_list` | error | an inline list contains another `[` at the same level | `sections.<key>` |
| `unknown_escape` | error | a double-quoted scalar uses an escape outside `\n`, `\t`, `\\`, `\"` | `sections.<key>` |
| `unterminated_quote` | error | a quoted scalar is unterminated or mismatched | `sections.<key>` |
| `duplicate_key` | warning | a registered fenced key appears more than once; first wins | `sections.<key>` |
| `reserved_value` | warning | a reserved gate stage / execution value appears | `sections.<key>[n].stage` / `sections.<key>[n].execution` |
| `reserved_field` | warning | a reserved `model_routing.when` field appears | `sections.model_routing....when` |
| `unknown_fence_key` | warning | a `beislid:*` key is not in the fence registry | `sections.<key>` |

## Notes

- Registered-but-not-target keys are parsed for syntax and then skipped silently by the normalizer.
- `workflow.md` conformance cases should prefer explicit absolute-line assertions in messages when a parser diagnostic is expected.
- Add new cases instead of mutating old ones unless you are intentionally changing the contract.
