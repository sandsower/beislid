# setup section agent-isolation v1

In verbose mode, emit `✓ setup/section-agent-isolation v1 loaded` immediately after reading this file.

## Agent isolation

Configure the canonical `beislid:agent_isolation` block under `Agent isolation`.
Explain that configuration requests strategy but does not claim host capability, and an absent block preserves legacy behavior.

Ask one value at a time:

```text
Orchestrator placement? (current / native / manual) [current]
Mutating delegate placement? (native / manual / sequential) [sequential]
Manual worktree root? (repo-sibling / absolute path) [repo-sibling]
Delegate fallback? (manual / sequential) [sequential]
Optional preparation command? [none]
```

Always write `fallback.orchestrator: manual-transition-required`.
Reject temporary roots such as `/tmp`, `/private/tmp`, and `/var/tmp`.
Explain that native or manual mutation becomes usable only after the host adapter passes end-to-end conformance, otherwise the configured fallback applies.

When preparation is configured, ask for zero or more read-only readiness commands.
Preparation must exit zero and leave tracked files unchanged before readiness checks run.

Ask whether the workflow needs atomic runtime profiles.
For each profile collect a lowercase name, every required uppercase binding name, and non-empty provider commands for allocate, verify, release, and reconcile that invoke checked-in provider scripts or reference named environment variables.
Reject provider commands containing embedded credential values before writing the block.
Explain that one profile bundles all database and service entrypoints that must isolate together, partial allocation rolls back, and secret values never enter workflow.md or ledger artifacts.

```beislid:agent_isolation
orchestrator: native
delegate: manual
manual_root: repo-sibling
fallback:
  orchestrator: manual-transition-required
  delegate: sequential
preparation:
  command: 'python3 scripts/prepare_workspace.py'
  readiness:
    - 'python3 scripts/check_workspace_ready.py'
runtime_profiles:
  integration:
    required_bindings:
      - PRIMARY_DATABASE_URL
      - SHADOW_DATABASE_URL
    provider:
      allocate: 'python3 scripts/runtime_provider.py allocate'
      verify: 'python3 scripts/runtime_provider.py verify'
      release: 'python3 scripts/runtime_provider.py release'
      reconcile: 'python3 scripts/runtime_provider.py reconcile'
```

Do not add action approvals to this block.
Authorization stays in `beislid:action_policy` under the stable `agent.*` action IDs.
Never create duplicate `beislid:agent_isolation` blocks; update or remove the existing one.
