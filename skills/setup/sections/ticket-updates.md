# setup section ticket-updates v1

In verbose mode, emit `✓ setup/section-ticket-updates v1 loaded` immediately after reading this file.

## Ticket updates

Configure the canonical `ticket_update` block.
This is shared by kickoff, review-response, and babysit: kickoff uses only the comment channel to post the approved implementation plan; review-response uses the comment channel for QA/ticket replies and the issue channel for out-of-scope child tickets; babysit's `cleanup` closeout stage uses the close channel to close the merged ticket and assign it to the PR author.

Ask for one mode:

```text
Configure ticket updates? (mcp / cli / skip)
```

For `mcp`, ask for `comment_tool` first, `issue_tool` second, and `close_tool` third.
The issue tool is optional; if omitted, review-response prints child-ticket drafts manually.
The close tool is optional and must be able to set an existing ticket's state and assignee; if omitted, babysit cleanup prints the manual close step instead.

```beislid:ticket_update
type: mcp
comment_tool: mcp__linear__save_comment
issue_tool: mcp__linear__save_issue
close_tool: mcp__linear__save_issue
```

For `cli`, ask for `comment_command` first, `issue_command` second, and `close_command` third.
Commands must use temp-file placeholders so user-authored text is never interpolated into the shell: `{id}` and `{body_file}` for comments; `{title_file}` and `{body_file}` for issues.
If the user proposes `{body}` or `{title}`, explain the injection/quoting risk and ask for a file-based command instead.
The close command is optional and carries no user-authored body, so it takes `{id}` plus optional `{state}` and `{assignee}`.

```beislid:ticket_update
type: cli
comment_command: '... {id} ... {body_file} ...'
issue_command: '... {title_file} ... {body_file} ...'
close_command: '... {id} ... {state} ... {assignee} ...'
```
