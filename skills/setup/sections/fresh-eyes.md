# setup section fresh-eyes v1

In verbose mode, emit `✓ setup/section-fresh-eyes v1 loaded` immediately after reading this file.

## Fresh-eyes final review

Configure the canonical `fresh_eyes` block under `Ready-for-review` or `Skill-specific overrides`.
Explain this affects only the final whole-diff `fresh-eyes` pass; the primary `review` pass still runs.

Ask:

```text
Configure final fresh-eyes behavior? (built-in / command / disable)
```

For `built-in`, remove any existing `fresh_eyes` block.
For `command`, ask for the command; it must be a repo-root command whose exit status signals blocking findings.
Write:

```beislid:fresh_eyes
type: command
command: '<user command>'
```

For `disable`, ask for a short reason and write:

```beislid:fresh_eyes
enabled: false
reason: '<reason>'
```

Never create duplicate `beislid:fresh_eyes` blocks; update or remove the existing one.
