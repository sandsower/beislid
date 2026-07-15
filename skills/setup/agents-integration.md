# setup AGENTS integration v1

In verbose mode, emit `✓ setup/agents-integration v1 loaded` immediately after reading this file.

The block content is fixed:

```markdown
## Agent skills

This repo uses [Beislið](https://github.com/sandsower/beislid) for orchestrator skills.

- Read `.beislid/workflow.md` first.
- Existing ticket or branch → `kickoff`
- Clear requirements, implementation still undecided → `blueprint`
- Work is done but not yet proven → `verify`
- Branch is ready for PR → `ready-for-review`
- Use direct skill invocation when the right entry point is already obvious.
- Run `/setup` when the repo workflow config is missing or needs updating.

- Project config: `.beislid/workflow.md`
- Audit setup: `/doctor`
- Configure: `/setup`
```

Insertion logic:

- If `<git-toplevel>/AGENTS.md` exists:
  - Look for an existing `## Agent skills` heading.
    If found, replace the content between that heading and the next `##` (or EOF) - keep the heading position where it is.
  - If no existing heading, append the block at end of file.
- If `AGENTS.md` does not exist:
  - Create it with just the block.
  - Even if `CLAUDE.md` exists, do NOT modify it.

Print:

```
📝 <added|updated> ## Agent skills section in <AGENTS.md path>
```
