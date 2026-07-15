# setup section clean-evaluator v1

In verbose mode, emit `✓ setup/section-clean-evaluator v1 loaded` immediately after reading this file.

## Clean evaluator

Configure the canonical `clean_eval` block under `Ready-for-review` or `Skill-specific overrides`.
Explain that `mode: require` runs configured pre-PR gates in a clean worktree/container and that `mode: off` keeps the normal working-tree gate path.
The clean surface may be created locally or supplied by the host; artifacts and logs stay under the configured root or run-ledger clean-eval artifacts.

Ask:

```text
Configure clean evaluator? (off / require)
```

For `require`, ask for the preferred surface and artifact root:

```text
Preferred clean surface? (auto / worktree / container)
```

Default to `auto` and explain that it accepts either a received clean surface or a fresh one created for evaluation.
Then ask for an optional artifact root, defaulting to `.beislid/clean-eval`.
Before writing, require the artifact root to be a non-empty repository-relative path, reject absolute paths and any `..` traversal segment, and re-prompt on invalid input.
Write:

```beislid:clean_eval
mode: require
surface: auto
artifact_root: .beislid/clean-eval
```

For `off`, remove any existing `clean_eval` block.

Never create duplicate `beislid:clean_eval` blocks; update or remove the existing one.
