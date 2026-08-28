# setup section babysit v1

In verbose mode, emit `✓ setup/section-babysit v1 loaded` immediately after reading this file.

## Babysit

Configure the canonical `beislid:babysit` block under `Babysit` or `Skill-specific overrides`.
Explain that `/babysit` requires `/goal`; this config only controls the goal budget, PR loop behavior, and closeout automation.

Ask whether to configure a goal token budget or leave it unlimited.
Accept values such as `50k`, `100000`, or `1m`; omit the field when unlimited.

Ask for loop behavior:

```text
Use review-response for actionable feedback? (Y/n)
Run configured gates before babysit-owned pushes? (Y/n)
Wait interval seconds? [60]
Timeout minutes? [none]
```

Ask for closeout modes:

```text
Merge after green? (off / ask / auto)
Merge method? (repo-default / squash / merge / rebase)
Delete branch after merge? (y/N)
Run memento capture after closeout? (off / ask / auto)
Run retro after closeout? (off / ask / auto)
Apply accepted retro findings? (off / ask / auto)
Run cleanup after a successful merge? (inherit merge / off / ask / auto)
```

Cleanup is the last closeout stage. It proves nothing is unlanded, closes the ticket through the configured `ticket_update` issue channel, deletes the merged remote branch, and reports the worktree path and branch as ready for removal — it never removes them itself. Offer `inherit merge` as the default and omit `closeout.cleanup.mode` when the answer is `inherit merge`, since an absent key follows `closeout.merge.mode`.

Explain that `auto` removes routine babysit prompts only when action policy allows the side effect.
If policy asks, the skill asks; if policy denies, it stops.

```beislid:babysit
goal:
  token_budget: 50k
loop:
  use_review_response: true
  run_configured_gates_before_push: true
  wait_interval_seconds: 60
  timeout_minutes: 60
closeout:
  merge:
    mode: ask
    method: squash
    delete_branch: true
  memento:
    mode: ask
  retro:
    mode: ask
    apply_findings: ask
  cleanup:
    mode: ask
```

Never create duplicate `beislid:babysit` blocks; update or remove the existing one.
