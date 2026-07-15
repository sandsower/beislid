# setup section pr-review v1

In verbose mode, emit `✓ setup/section-pr-review v1 loaded` immediately after reading this file.

## PR review source / replies

If `git remote get-url origin` parses as GitHub and `gh auth status` passes, suggest GitHub CLI defaults:

```text
Use GitHub CLI to read PR reviews and post clear-fix replies? (Y / manual replies / n)
```

On `Y`, write both blocks:

```beislid:pr_review_source
type: cli
summary_command: 'gh pr view --json url,number,reviewDecision,reviews,comments'
threads_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments'
```

```beislid:pr_review_update
type: cli
reply_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments --method POST --input {json_file}'
rerequest_command: 'gh api repos/{owner}/{repo}/pulls/{number}/requested_reviewers --method POST --input {json_file}'
```

On `manual replies`, write the same `pr_review_source` and this update block:

```beislid:pr_review_update
type: manual
```

On `n`, or when the repo is not GitHub/authed, ask for source mode: `cli / paste / skip`.

For source `cli`, ask for `summary_command` first.
It may use `{owner}`, `{repo}`, `{number}`, and `{url}` placeholders; if it uses any of those, setup should remind the user that review-response will derive or ask for the values at runtime.
Then ask for optional `threads_command` for inline review comments.
Write:

```beislid:pr_review_source
type: cli
summary_command: '<user command>'
# Include threads_command only when the user supplies one.
threads_command: '<user command>'
```

For source `paste`, write an explicit manual source:

```beislid:pr_review_source
type: paste
```

If a source is configured, ask for update mode: `cli / manual / skip`.

For update `cli`, ask for `reply_command` first and require a `{json_file}` placeholder.
The command may also use `{owner}`, `{repo}`, and `{number}`.
Then ask for optional `rerequest_command`; if supplied, it must also use `{json_file}`.
Write:

```beislid:pr_review_update
type: cli
reply_command: '<user command with {json_file}>'
# Include rerequest_command only when the user supplies one.
rerequest_command: '<user command with {json_file}>'
```

For update `manual`, write `type: manual`; `skip` leaves update absent and review-response prints manual instructions.
