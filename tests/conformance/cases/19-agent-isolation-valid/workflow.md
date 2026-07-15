<!-- beislid-workflow: v1 -->

```beislid:agent_isolation
orchestrator: native
delegate: manual
manual_root: repo-sibling
fallback:
  orchestrator: manual-transition-required
  delegate: sequential
runtime_profiles:
  integration:
    required_bindings:
      - PRIMARY_DATABASE_URL
      - SHADOW_DATABASE_URL
      - REDIS_URL
    provider:
      allocate: 'python3 scripts/runtime_provider.py allocate'
      verify: 'python3 scripts/runtime_provider.py verify'
      release: 'python3 scripts/runtime_provider.py release'
      reconcile: 'python3 scripts/runtime_provider.py reconcile'
```
