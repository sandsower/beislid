# babysit cleanup protocol v1

In verbose mode, emit `✓ babysit/cleanup-protocol v1 loaded` immediately after reading this file.

Load this file at the `cleanup` closeout stage, after `merge`, `memento`, and `retro` have each run or been skipped. Cleanup is reachable only after a successful merge; a green-but-unmerged endpoint never reaches it.

## Mode

`closeout.cleanup.mode` is `off`, `ask`, or `auto`. When the key is absent it follows `closeout.merge.mode`, so a repo that already auto-merges gets cleanup with no config change. `off` skips the stage and reports it as skipped. `ask` shows the planned ticket close, remote-branch delete, and local-copy report, then waits for approval. `auto` proceeds only where action policy allows each side effect.

## Step 1 — prove nothing is unlanded

Run no later step until all of these hold. Report and stop otherwise; never discard, reset, stash, or force anything.

- The PR is merged according to configured PR host tooling, for example `gh pr view --json state,mergedAt`.
- `git status --porcelain` is empty, untracked files included.
- The default branch is freshly fetched (`git fetch <remote> <default>`) and `git diff <remote>/<default> HEAD` is empty.

A squash merge rewrites the branch into one new commit, so local commit SHAs will not appear on the default branch. Compare content, not SHAs; an empty tree diff is the check that works.

A non-empty tree diff does not prove unlanded work on its own — the default branch may have advanced with unrelated commits. Intersect the paths this branch touched with the paths that still differ from the default branch:

```bash
base=$(git merge-base <remote>/<default> HEAD)
comm -12 \
  <(git diff --name-only "$base" HEAD | sort) \
  <(git diff --name-only <remote>/<default> HEAD | sort)
```

Intersect the two path lists as text. Do not restrict the second diff with a git pathspec instead: `git diff` has no `--pathspec-from-file`, and passing the paths as pathspec arguments lets `*`, `?`, or `[...]` in a filename be read as glob magic, so a path like `pages/[id].tsx` silently matches nothing and unlanded work reads as landed.

Empty output means this branch's content landed and cleanup may continue. Any listed path is unlanded work: stop, name every path, and hand the branch back untouched.

Policy: verification is `read`, plus `network-read` for the fetch.

## Step 2 — close the ticket

Resolve the ticket from run context or `branch_pattern`. Close it through the configured `ticket_update` close channel — `close_tool` when `type: mcp`, `close_command` when `type: cli` — and assign it to the PR author. Read the tracker from `workflow.md`; never hardcode Linear, Jira, GitHub Issues, or any other tracker.

Skip this step and say so when no `ticket_update` is configured or no ticket was resolved for this branch. With no close channel, fall back to the issue channel only when it can set an existing ticket's state and assignee; the CLI `issue_command` cannot, because its placeholders are `{title_file}` and `{body_file}` with no ticket id. When no configured channel can express the change, print the exact manual close step instead of inventing a command.

Policy: `ticket.update` plus `tracker.issue.transition`, classes `network-read` and `git-remote`.

## Step 3 — delete the remote branch

Delete it only when `closeout.merge.delete_branch` is true and the ref still exists (`git ls-remote --heads <remote> <branch>`); the merge may already have deleted it. Never delete the default branch. Use configured PR host tooling where it has a branch-delete verb, and fall back to `git push <remote> --delete <branch>` when it does not; do not invent a host-specific API call. Some PR hosts fail the branch-delete step of a merge when it runs from a secondary worktree, which is exactly the gap this step covers.

Policy: `git.remote.branch.delete`, class `git-remote`.

## Step 4 — report the local copy as ready for removal

Name the worktree path (`git rev-parse --show-toplevel`) and the branch name, and state that both are ready to be removed by the supervising session.

## Cleanup never removes its own worktree

Do not remove the worktree. Do not delete the local branch. The agent is running inside that worktree; removing it kills the session mid-report and loses the outcome the supervising session is waiting for. Reporting the path is the whole job, and the supervising session removes it afterwards.

This is deliberate, not an oversight. Do not "fix" it by adding `git worktree remove`, `git branch -d`, or any equivalent local deletion.
