# setup section translation-sync v1

In verbose mode, emit `✓ setup/section-translation-sync v1 loaded` immediately after reading this file.

## Translation sync

Configure `translation_sync.skill` and `translation_sync.trigger_paths` only when the repository has an installed translation-sync skill and known trigger globs.
Ask for the skill name, then collect one or more repo-relative trigger globs.
Explain that ready-for-review invokes the skill when a changed path matches.
Never create duplicate keys; update or remove the existing pair together.
