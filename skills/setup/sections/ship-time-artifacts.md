# setup section ship-time-artifacts v1

In verbose mode, emit `✓ setup/section-ship-time-artifacts v1 loaded` immediately after reading this file.

## Ship-time planning-artifact handling

Configure ship-time planning-artifact narration? (remind / include / skip / clean)

Explain that `ship_time_artifacts` only changes how ready-for-review summarizes generated planning artifacts during handoff.
It consults configured planning-artifact lifecycle actions and does not auto-commit or auto-delete files in v1.

```beislid:ship_time_artifacts
mode: remind
```

For `skip`, remove any existing block.
