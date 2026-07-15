# setup section model-routing v1

In verbose mode, emit `✓ setup/section-model-routing v1 loaded` immediately after reading this file.

## Model routing

Configure the canonical `model_routing` block under `Model routing` or `Skill-specific overrides`.
Explain that this is a host-adapter hint/enforcement contract: hosts honor it only when model selection is supported, report the routing status, and block only for `mode: require` when no candidate can be honored.

Ask for an optional default route, then ordered skill overrides.
For each route collect:

- skills list (overrides only), using Beislið skill names such as `spec`, `blueprint`, `implement`, `review`, `fresh-eyes`, `ready-for-review`, and `review-response`
- model candidates as an ordered list; `model` may be written only as shorthand for a single candidate, otherwise write `models`
- mode: `prefer` or `require`, default `prefer`

Prefer portable aliases (`opus`, `sonnet`, `haiku`, `default`, `host-default`), but allow namespaced provider strings as escape hatches.
Do not collect `when:` conditions in v1; say conditional routing is reserved for later workflow support and should not be written as active config.

```beislid:model_routing
defaults:
  models: [sonnet]
  mode: prefer
overrides:
  - skills: [spec, blueprint, poke-holes]
    models: [opus, openai:gpt-5.5]
    mode: require
```

If the repo also ships a `WORKFLOW.md` Rondo profile, keep its `step_hints` adapter in sync with the same tier table: kickoff initial spawn should route stronger than the broad default, ideally `heavy`/`frontier`; ordinary implementation should stay on `standard`; ready-for-review gate execution can stay `light` or `standard`; and review/fresh-eyes synthesis should escalate to `heavy`.
`when:` remains reserved there as well.

Never create duplicate `beislid:model_routing` blocks; update or remove the existing one.
