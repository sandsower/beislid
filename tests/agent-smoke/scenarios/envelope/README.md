# envelope smoke scenario

Exercises the `/envelope` walking skeleton end-to-end against a fixture repo with a pre-approved
break-spec structure (`plans/widget-export-structure.md`), skipping the planning conversation.

Asserts:

- bundle exported to `.beislid/exports/wid-7-widget-export/` and `scripts/validate_export.py` exits 0
- bundle `status: approved`, every child slice has `slices/<id>.json` + `.md`
- slice manifest is `approved-slice-v1` with the templated prompt sections, `repo` pinning
  (`url`, `base_ref`, `base_sha`), and `allowed_actions` lists
- `.beislid/checkpoints/latest.json` carries an `envelope_exported` pointer from skill `envelope`
- the bundle was committed (`Export envelope bundle ...`)
- the four step aux files were actually loaded (verbose stamps)

The fixture workflow.md allow-lists `export.bundle.write`, `checkpoint.envelope_exported`, and
`git.commit` in supervised-auto so the non-interactive run can cross its side-effect boundaries.

Run: `python3 tests/agent-smoke/run.py envelope --host codex`
