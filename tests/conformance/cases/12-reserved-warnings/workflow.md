<!-- beislid-workflow: v1 -->

```beislid:gates
- name: lint
  command: 'pnpm lint'
  stage: someday
  execution: psychic
```

```beislid:model_routing
defaults:
  model: anthropic:claude-sonnet-4.5
  when:
    branch: main
```
