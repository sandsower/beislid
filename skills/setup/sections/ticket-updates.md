# setup section ticket-updates v1

In verbose mode, emit `✓ setup/section-ticket-updates v1 loaded` immediately after reading this file.

## Ticket updates

Configure the canonical `ticket_update` block.
This is shared by kickoff and review-response: kickoff uses only the comment channel to post the approved implementation plan; review-response uses the comment channel for QA/ticket replies and the issue channel for out-of-scope child tickets.

Ask for one mode:

```text
Configure ticket updates? (mcp / cli / skip)
```

For `mcp`, ask for `comment_tool` first and `issue_tool` second.
The issue tool is optional; if omitted, review-response prints child-ticket drafts manually.

```beislid:ticket_update
type: mcp
comment_tool: mcp__linear__save_comment
issue_tool: mcp__linear__save_issue
```

For `cli`, ask for `comment_command` first and `issue_command` second.
Commands must use temp-file placeholders so user-authored text is never interpolated into the shell: `{id}` and `{body_file}` for comments; `{title_file}` and `{body_file}` for issues.
If the user proposes `{body}` or `{title}`, explain the injection/quoting risk and ask for a file-based command instead.

```beislid:ticket_update
type: cli
comment_command: '... {id} ... {body_file} ...'
issue_command: '... {title_file} ... {body_file} ...'
```
