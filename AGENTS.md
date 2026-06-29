# Beislið bootstrap guidance

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
