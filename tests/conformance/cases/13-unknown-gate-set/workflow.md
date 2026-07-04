<!-- beislid-workflow: v1 -->

```beislid:gate_sets
sets:
  fast:
    gates:
      - name: lint
        command: 'pnpm lint'
selectors:
  - paths: ['**']
    gate_sets: [fast, missing]
```
