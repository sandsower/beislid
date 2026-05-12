---
name: handoff
description: Use when splitting work to another agent, session, or worktree; creating a paste-ready context handoff; or when the user asks to "handoff frontend", "handoff backend", "handoff QA", "handoff migration", or copy context for another coding agent. Do not use for same-session resume; use a dedicated resume workflow if available.
---

# Handoff

Create a paste-ready opening prompt for another agent/session/worktree. This skill is read-only in the parent workspace except for copying text to the local clipboard.

Use this when:
- Work is being split across parallel sessions or worktrees
- The user wants a scoped context packet for another coding agent
- The user says things like "handoff frontend", "handoff backend", "handoff QA", or "make a handoff for the migration"

Do not use this when:
- Resuming the same work in the same session — use a dedicated resume workflow if available
- Starting a fresh ticket from the tracker — use `kickoff`
- Saving long-term session memory — use `memento` if available

<HARD-GATE>
Do not create tickets, commits, branches, worktrees, or cross-worktree file changes. Do not include full diffs. Do not infer decisions that were not explicitly stated.
</HARD-GATE>

## Process

### 1. Determine the slice

If the user's request includes a clear slice, proceed. Clear slices include:
- domain words: frontend, backend, mobile, QA, test, migration, infra, docs
- named files, directories, components, services, or APIs
- an explicit task statement

If the user only says "handoff" or gives vague scope like "some of this", ask one clarifying question:

> What slice should I hand off — frontend, backend, QA, migration, or something else?

Do not gather context until the slice is clear.

### 2. Gather read-only workspace state

Run simple read-only commands. Avoid compound commands when the host prompts for bash permissions.

Required:

```bash
pwd
git branch --show-current
git status --short
git diff --stat
```

Optional, if relevant and cheap:

```bash
git log --oneline -5
find plans -maxdepth 2 -type f
```

Only read plan/spec/design files if they are directly relevant to the requested slice. Do not read or paste full diffs.

### 3. Extract explicit context

Build the handoff from:
- the user's stated goal
- the requested slice
- explicit decisions made in this conversation
- relevant written artifacts you read
- current git state from the required commands

Be conservative:
- If a decision was not explicitly stated, put it under **Open questions**
- Do not infer architecture from code patterns unless the user or artifact named it
- Do not include secrets, credentials, tokens, or private values
- Do not include full diff hunks

### 4. Write the payload

The payload must be agent-neutral. Do not assume the receiver has Beislið, Claude Code, Codex, pi, or slash commands.

Use this structure:

```markdown
# Handoff: <slice>

You are taking over the <slice> slice of this work in a separate session/worktree.

## Goal
<One or two sentences describing the overall goal and this slice's assignment.>

## Parent workspace state
- Parent path: `<pwd>`
- Parent branch: `<branch>`
- Working tree summary:
  ```text
  <git status --short output or "clean">
  ```
- Diff stat:
  ```text
  <git diff --stat output or "no local diff">
  ```

## Assigned scope
- <What the receiving agent should work on>
- <Boundaries of the slice>

## Explicit decisions so far
- <Decision and rationale, only if explicitly known>

## Constraints / do not touch
- Do not assume unstated product or architecture decisions.
- Do not modify work outside the assigned slice without asking.
- Do not rely on the parent session transcript being available.
- <Any project-specific constraints surfaced by the parent session>

## Suggested first steps
1. Inspect the local repo/worktree state.
2. Read relevant plans/specs/docs named in this handoff.
3. Verify assumptions before editing.
4. Implement only the assigned slice.

## Open questions
- <Questions the receiver should resolve before proceeding, or "None known.">
```

Scale the payload to the work. Small handoffs can be short, but keep the section headings so the receiver can scan quickly.

### 5. Preview and copy

Always show the payload in the chat before or alongside copying.

Then copy immediately if a clipboard command is available. Try these in order:

```bash
command -v wl-copy
command -v xclip
command -v pbcopy
command -v clip.exe
command -v clip
```

Copy using the first available command:

```bash
printf '%s' '<payload>' | wl-copy
printf '%s' '<payload>' | xclip -selection clipboard
printf '%s' '<payload>' | pbcopy
printf '%s' '<payload>' | clip.exe
printf '%s' '<payload>' | clip
```

If shell quoting would be fragile, write the payload to a temporary file, copy from that file, then remove it:

```bash
mktemp
# write payload to temp file using the host's file write/edit tool
wl-copy < /tmp/<file>
rm /tmp/<file>
```

If no clipboard command is available, say so and leave the payload printed for manual copy.

## Output Requirements

After copying or falling back, end with:
- whether clipboard copy succeeded
- which clipboard command was used, if any
- a reminder that the parent workspace was not modified

## Common Mistakes

| Mistake | Fix |
|---|---|
| Bare handoff proceeds with guessed scope | Ask what slice to hand off |
| Payload tells receiver to run Beislið commands | Keep it agent-neutral |
| Includes full `git diff` | Use `git diff --stat` only |
| Infers decisions from code shape | Move uncertain items to Open questions |
| Creates a worktree or branch | Stop; handoff is copy-only |
| Skips preview because clipboard succeeded | Always show the payload |
