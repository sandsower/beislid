# setup section ship-time-artifacts v1

In verbose mode, emit `✓ setup/section-ship-time-artifacts v1 loaded` immediately after reading this file.

## Ship-time planning-artifact handling

Configure ship-time planning-artifact narration? (remind / include / skip / clean)

Explain that `ship_time_artifacts` only changes how ready-for-review summarizes generated planning artifacts during handoff.
It consults configured planning-artifact lifecycle actions and does not auto-commit or auto-delete files in v1.

For `remind`, `include`, or `clean`, write the selected mode:

```beislid:ship_time_artifacts
mode: <selected-mode>
```

`clean` means the handoff narration identifies local-only planning artifacts as excluded from the shipped surface; it does not delete or rewrite them.

For `skip`, remove any existing block.
