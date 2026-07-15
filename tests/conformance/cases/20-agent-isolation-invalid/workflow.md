<!-- beislid-workflow: v1 -->

```beislid:agent_isolation
orchestrator: automatic
delegate: shared
manual_root: /private/tmp/beislid
fallback:
  orchestrator: sequential
  delegate: manual-transition-required
runtime_profiles:
  integration:
    required_bindings:
      - primary_database_url
      - primary_database_url
    provider:
      allocate: ''
      verify: 42
      release: 'python3 provider.py release'
```
