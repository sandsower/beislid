# setup write and report v1

In verbose mode, emit `✓ setup/write-and-report v1 loaded` immediately after reading this file.

## 8. Show preview

Print the composed workflow.md to the user as context, then ask the explicit approval question once in the final response:

```
📋 Preview of `.beislid/workflow.md`:

<composed contents>

Write this to `<git-toplevel>/.beislid/workflow.md`? [Y/n]
```

On `n`: cancel without writing.
On `Y`: continue to step 9.

## 9. Write workflow.md and insert AGENTS.md block

Run `mkdir -p <git-toplevel>/.beislid/` then write the file.
Print:

```
📝 Wrote .beislid/workflow.md
```

Then run the AGENTS.md block insertion through [AGENTS integration](agents-integration.md).

After writing the minimum, offer the menu mode through [menu mode](menu.md) for adding optional sections.

## 10. Next-steps report after writes

After any successful `.beislid/workflow.md` write (first-run, add/change/remove, or reset), print a concise next-steps report:

```
✅ Beislið config written.

Files to review/commit:
- .beislid/workflow.md
- AGENTS.md (when added or updated)

Configured now: <ticket source, branch pattern, gates, PR reviews, ticket updates, etc.>
Not configured yet: <missing strictness layers, or "none obvious">

Next:
1. Run /doctor to verify the config and warm the probe cache.
2. Run each configured gate command once from the repo root.
3. Commit .beislid/workflow.md and AGENTS.md together.
4. For team rollout guidance, read the Beislið team rollout guide: https://github.com/sandsower/beislid/blob/main/docs/team-rollout.md.
```

Keep the report factual.
Do not imply unconfigured layers are required; present them as optional strictness layers to add deliberately later.
