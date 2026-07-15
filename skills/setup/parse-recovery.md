# setup parse recovery v1

In verbose mode, emit `✓ setup/parse-recovery v1 loaded` immediately after reading this file.

If `.beislid/workflow.md` exists but doesn't parse cleanly per `workflow-md-format.md` grammar, run the same line-numbered diagnosis doctor uses:

```bash
grep -n '^```beislid:' <repo>/.beislid/workflow.md
```

Compute the line number of the failing block, surface it in prose:

```
🛑 Workflow.md has a parse error.

⚠️ The `beislid:<key>` block at line <N> doesn't parse: <yaml error>.

✓ The other configured sections (<list>) parsed cleanly.

What now?
  (a) Reset and regenerate from scratch - saves current file to
      `.beislid/workflow.md.bak` first.
  (b) Cancel - exit setup, fix workflow.md by hand or run /doctor for more
      detail.
```

On `(a)`: run the Reset option in [menu mode](menu.md).
On `(b)`: exit cleanly.

Don't offer Add / Change / Remove on a partially parseable file - they're unsafe without a clean parse of every section.
