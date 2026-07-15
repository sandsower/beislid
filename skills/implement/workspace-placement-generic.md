# workspace placement generic adapter v1

Unknown hosts start with no native placement capability.
Documentation or a worktree command alone cannot upgrade that state.

For a top-level transition, create a durable manual worktree only when requested, print the absolute path and expected SHA, return `manual-transition-required`, and stop before mutation.
The relaunched session must acknowledge the destination and rerun universal preflight.

For a mutating delegate, manual placement is `verified-manual` only when the host can enforce the assigned absolute working directory and deliver the placement identity and runtime profiles.
Otherwise report `unavailable` and execute sequentially.

Never create user-visible child tasks as a substitute for subagent isolation.
Never adopt existing paths or branches, and never use an ephemeral directory as the sole progress copy.

Require the universal receipt, acknowledgment, committed handoff, serial integration, verification, lease release, and ownership-aware cleanup rules.
Use `cleanup_owner: beislid` only for helper-created worktrees, `host` only when a verified host API owns cleanup, and `user` when ownership is unknown.
