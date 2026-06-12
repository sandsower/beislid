# envelope smoke scenario

Exercises the `/envelope` batch flow end-to-end against a fixture repo with two pseudo-tickets,
each backed by a pre-approved break-spec structure (`plans/widget-export-structure.md` for WID-7,
`plans/widget-report-structure.md` for WID-8), skipping the planning conversation. The WID-8
report slice consumes the CSV the WID-7 export slice produces (cross-ticket dependency).

Asserts:

- ONE bundle exported to `.beislid/exports/wid-7-wid-8-widget-suite/` and `scripts/validate_export.py` exits 0
- bundle `status: approved`, exactly two children with `source_ticket` WID-7 and WID-8,
  every child slice has `slices/<id>.json` + `.md`
- `dependency_graph` carries the cross-ticket edge (WID-8 slice depends on WID-7 slice, not reversed)
- `slice_plan.parallel_groups` present and the dependent slices do not share a group
- slice manifest is `approved-slice-v1` with the templated prompt sections, `repo` pinning
  (`url`, `base_ref`, `base_sha`), and `allowed_actions` lists
- `.beislid/checkpoints/latest.json` carries an `envelope_exported` pointer from skill `envelope`
- the bundle was committed (`Export envelope bundle ...`)
- the four step aux files were actually loaded (verbose stamps)

The fixture workflow.md allow-lists `export.bundle.write`, `checkpoint.envelope_exported`, and
`git.commit` in supervised-auto so the non-interactive run can cross its side-effect boundaries.

Run: `python3 tests/agent-smoke/run.py envelope --host codex`
