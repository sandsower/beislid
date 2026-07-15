# setup section browser-compatibility v1

In verbose mode, emit `✓ setup/section-browser-compatibility v1 loaded` immediately after reading this file.

## Browser compatibility

Configure `browser_compat.skill` and `browser_compat.trigger_paths` only when the repository has an installed browser-compatibility skill and known trigger globs.
Ask for the skill name, then collect one or more repo-relative trigger globs.
Explain that the check is advisory during ready-for-review and does not become a blocking quality gate.
Never create duplicate keys; update or remove the existing pair together.
