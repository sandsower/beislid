<!-- beislid-workflow: v1 -->

```beislid:scopes
- name: frontend
  paths: ['apps/web/**']
  gates:
    - name: lint
      command: 'pnpm lint'
```

```beislid:gates
- { name: lint, command: 'pnpm lint' }
```
