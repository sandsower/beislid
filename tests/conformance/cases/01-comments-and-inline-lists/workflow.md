<!-- beislid-workflow: v1 -->

```beislid:gates
- name: lint
  parallel_safe: true # optional
  autofix: npm run lint -- --fix # optional
  command: 'echo "a # b"'
  paths: [docs/**, *.md # optional]
```
