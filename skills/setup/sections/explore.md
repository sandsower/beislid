# setup section explore v1

In verbose mode, emit `✓ setup/section-explore v1 loaded` immediately after reading this file.

## Explore skill

Configure the canonical `explore` block under the `Kickoff` / skill-specific overrides section.

Ask:

```
Configure kickoff explore skill? (enhance / replace / skip)
```

For `enhance` or `replace`, ask for the skill name.
Explain that `enhance` keeps default codebase exploration and merges skill findings; `replace` uses the skill instead and falls back to default exploration only after a runtime prompt if the skill fails.

```beislid:explore
skill: <skill-name>
mode: enhance
```
