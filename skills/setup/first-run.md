# setup first run v1

In verbose mode, emit `✓ setup/first-run v1 loaded` immediately after reading this file.

## 3. First-run: targeted inspection

Run cheap-signal commands once at the top, before asking anything:

```bash
git remote get-url origin                              # → host + owner/repo
gh auth status 2>&1                                    # → is gh CLI logged in?
git log -50 --pretty=%s                                # → grep for ID patterns
git for-each-ref refs/heads --format='%(refname:short)' --sort=-committerdate \
  | head -20                                           # → branch_pattern candidates
```

Parse `git remote` for host (`github.com` / `gitlab.com` / etc.) and `owner/repo`.
Parse `gh auth status` for the auth state on github hosts.
Grep commit subjects for `[A-Z]{2,4}-\d+` (Linear/Jira shape) and `^#?\d+` (GitHub/Azure numeric shape).
Hold these results in memory for the interview prompts.

## 4. First-run: ticket_source interview

Use the inspection results to suggest a default.
One suggestion at a time, single Y/n confirmation; never silent fill.

**If host is github.com + gh authed + numeric IDs detected in commits:**

```text
🔍 Detected GitHub Issues with `gh` CLI (numeric IDs in recent commits).
Use `type: cli, command: 'gh issue view {id} --json title,body,labels'`?
[Y/n/different]
```

On `Y`: capture `id_pattern: '^#?\d+$'` and `link_template: 'https://github.com/<owner>/<repo>/issues/{id}'` (deterministic from `git remote`).

**If Linear-shaped IDs detected (`[A-Z]+-\d+`):**

Try MCP discovery via `probe-semantics.md` (search for tools matching `*linear*` or `*issue*`).
On match:

```text
🔍 Linear-shaped IDs in recent commits + Linear MCP tool detected
(`<tool-name>`). Use this for ticket fetching? [Y/n/different]
```

On `Y`: capture `type: mcp, tool: <tool-name>, id_pattern: '^[A-Z]+-\d+$'`.
Ask once for the workspace name to populate `link_template: 'https://linear.app/<workspace>/issue/{id}'`.
If the host resolves the same integration through an alias, keep the configured tool name canonical and let the probe report the alias-satisfied match instead of forcing a session-local override.

If MCP discovery returns no Linear-shaped tools: do NOT ask the user to type an MCP tool name.
Pivot:

```text
💭 Linear-shaped IDs detected but no Linear MCP tool is available in this
host. Pick an alternative:
  (a) cli - give me the command for fetching tickets
  (b) paste - I'll ask for the title at every PR handoff
```

**If no detectable signal:** ask `(mcp / cli / file / paste)` directly.
For `mcp`: list available MCP tools via `probe-semantics.md` and ask to pick one.
For `cli`: ask for the command (must contain `{id}` placeholder).
For `file`: ask for the file glob.
For `paste`: no further input.

In every branch, capture `id_pattern` (auto-derived from the dominant grep pattern) and `link_template` for known hosts (deterministic).
Never ask the user to type an MCP tool name.

## 5. First-run: branch_pattern interview

Test these 8 candidate regexes against the last 20 branches.
Sort by coverage (number of branches that match).

```text
1. ^[a-z]+/([a-z]+-\d+)       - case-mismatched (normalize via id_pattern)
2. ^[a-z]+/([A-Z]+-\d+)       - Jira with type prefix
3. ^([A-Z]+-\d+)              - Jira/Linear direct uppercase
4. ^([a-z]+-\d+)              - direct lowercase
5. ^(\d+)-                    - github/azure numbered with description
6. ^[a-z]+/(\d+)              - feature/123 (Azure DevOps, GitHub)
7. ^[a-z]+/[a-z]+/(\d+)       - Azure DevOps users/<name>/12345
8. ^[a-z]+-(\d+)              - gh-123 style
```

Suggest the highest-coverage candidate with stats:

```text
🔍 Branch pattern `^[a-z]+/([a-z]+-\d+)` matches 18 of 20 recent branches.
Use it? [Y/n/skip]
```

If best coverage <60%: don't suggest a pattern.
Ask:

```text
💭 No regex covers most recent branches. Skip branch_pattern? Ready-for-review will
ask for the ticket ID at every run. [Y/n]
```

On `n`: ask for the regex directly.
On `Y` (skip): capture nothing for branch_pattern.

## 6. First-run: pr_base interview

Probe order:

1. If host is github.com + gh authed: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.
2. Else: `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'`.
3. Else: `main`.

If the result is `main`: silent default - don't ask.
If the result is anything else, confirm:

```text
🔍 Default branch detected: `<branch>`. Use as pr_base? [Y/n]
```

On `n`: ask the user for the branch name.

## 7. First-run: compose minimum workflow.md

Compose in memory:

- Version stamp `<!-- beislid-workflow: v1 -->` (line 1).
- Project name comment from `basename $(git rev-parse --show-toplevel)`.
- `## Issue tracker` section with the captured `ticket_source` and (if present) `branch_pattern` blocks.
- `## PR target` section with `pr_base.default` (only if non-`main`).
- `## Probe cache` section with `ttl_hours: 24`.

No commented-out templates.
Only sections the user filled in.
