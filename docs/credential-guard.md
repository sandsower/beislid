# credential_guard

Opt-in PreToolUse hook. Blocks Bash commands that would print secret values to the terminal — `printenv`, bare `export`, `cat` of key files, echo of `$*_TOKEN`-style vars, and commands referencing `.env`, `credentials.json`, `.netrc`, `.pgpass`, and similar paths. Stdlib-only Python 3.

## Enable

1. Install with the flag:

   ```
   ~/Projects/beislid/install.sh --with-security-hooks
   ```

   Requires `python3` on PATH. install.sh fails early if it's missing. Both `credential_guard.py` and its sibling `credential_guard.json` are symlinked into `~/.claude/hooks/`.

2. Register the hook in `~/.claude/settings.json`:

   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Bash",
           "hooks": [
             {
               "type": "command",
               "command": "python3 $HOME/.claude/hooks/credential_guard.py",
               "timeout": 5
             }
           ]
         }
       ]
     }
   }
   ```

3. Restart Claude Code.

## Customize

The hook includes sensible defaults. Three override paths, in order of precedence:

- `CREDENTIAL_GUARD_CONFIG=/path/to/my-config.json` in your shell. Use this if you want local-only config that never lives in a repo.
- Edit `hooks/credential_guard.json` in this repo. install.sh symlinks it into `~/.claude/hooks/credential_guard.json`, so your edits take effect on next tool call. Changes are tracked by git.
- If neither is present, the built-in `DEFAULT_CONFIG` applies.

The hook reads its sibling JSON by resolving `__file__` through symlinks, so the config lookup works whether you invoke the script via its real path or its installed symlink.

Config schema:

```json
{
  "blocked_commands":   ["printenv", "env", ...],
  "blocked_substrings": [".env", "TOKEN", ...],
  "blocked_patterns":   ["cat.*id_rsa", ...],
  "blocked_pipes":      ["env |", "printenv |", ...],
  "allow_export_with_args": true,
  "allowed_markers":    ["hooks/memento-remote-sync.py"]
}
```

- `blocked_patterns` are case-insensitive regex.
- `allow_export_with_args` lets `export VAR=value` through while still blocking bare `export`.
- `allowed_markers` is a substring allowlist checked *before* any block rule. If a command contains any marker, it passes unconditionally. Use sparingly: markers must be specific enough that no unrelated command could contain them (a path to a trusted script is the typical case; a generic word like `memento` is not).

## Why opt-in

The hook is strict. False positives happen:

- `.env.example` trips the `.env` substring.
- Commit messages and PR bodies are stripped before substring checks (heredocs and `-m "..."`), but prose *outside* those forms that mentions `TOKEN` will block.
- Any script that legitimately runs `printenv | grep FOO` is blocked.

You should know what you're enabling. For most dev work the tradeoff is worth it; for scripts that legitimately inspect env, turn it off or narrow the config.

## Marketplace install

Not yet. v0.1.0 supports install.sh only. When Beislið submits to a plugin marketplace (v0.2+), the hook will register automatically via `.claude-plugin/hooks.json` and this manual settings.json step goes away.
