# BEI-77 Model Landscape Research

**Status:** research draft
**Date:** 2026-06-28
**Scope:** provider-neutral capability-tier defaults for BEI-76/BEI-77 follow-up work. This is a research note, not the BEI-76 export manifest.

## Method

- Source cut: current public vendor docs fetched in-session (Anthropic, OpenAI, Google) plus OpenRouter model pages for open-weight coverage.
- Cost numbers below are **uncached first-pass estimates**. They exclude tool-call fees and ignore prompt-cache savings.
- When vendor docs and benchmark/attempt-chain results disagree, **benchmark data wins**.
- Lifecycle status matters: deprecated/retired models are excluded from new defaults even if they still exist in legacy routing tables.

## What the landscape says

### Anthropic

| Model | Context / long-context note | Price (input / output) | Posture | Research take |
| --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | not separately re-verified here | $1 / $5 per MTok | active | cheap, reliable small-model fallback |
| Claude Sonnet 4.6 | 1M-token long context at standard pricing | $3 / $15 per MTok | active | balanced code/test default |
| Claude Opus 4.8 | 1M-token long context at standard pricing | $5 / $25 per MTok | active | strongest Anthropic frontier candidate |
| Claude Opus 4.1 | legacy/deprecated | $15 / $75 per MTok | deprecated | exclude |
| Claude Sonnet 4 | retired | $3 / $15 per MTok | retired | exclude |
| Claude Haiku 3.5 | retired | $0.80 / $4 per MTok | retired | exclude |

Source: [Anthropic pricing](https://docs.anthropic.com/en/docs/about-claude/pricing) and [Anthropic deprecations](https://docs.anthropic.com/en/docs/about-claude/model-deprecations).

### OpenAI

| Model | Context | Price (input / output) | Posture | Research take |
| --- | --- | --- | --- | --- |
| GPT-5.1 | 400k context | $1.25 / $10 per MTok | flagship | strong general-purpose coding/agentic model |
| GPT-5.1-Codex | 400k context | $1.25 / $10 per MTok | active | best OpenAI fit for code+tests slices |
| GPT-5 | 400k context | $1.25 / $10 per MTok | previous model | superseded by GPT-5.1 |
| GPT-5.5 | no confirmable current model page in this pass | n/a | unconfirmed | exclude until officially documented |

Source: [GPT-5.1-Codex](https://platform.openai.com/docs/models/gpt-5.1-codex), [GPT-5.1](https://platform.openai.com/docs/models/gpt-5.1), [GPT-5](https://platform.openai.com/docs/models/gpt-5), [OpenAI pricing](https://platform.openai.com/docs/pricing).

### Google

| Model | Context | Price (input / output) | Posture | Research take |
| --- | --- | --- | --- | --- |
| Gemini 2.5 Flash | 1,048,576 input / 65,536 output | $0.25 / $1.50 per MTok | active | best low-cost general/light default |
| Gemini 2.5 Pro | 1,048,576 input / 65,536 output | $2 / $12 per MTok | active | best large-context synthesis backup |

Source: [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash), [Gemini 2.5 Pro](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-pro), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing).

### OpenRouter coverage models

| Model | Context | Price (input / output) | Benchmarks / posture | Research take |
| --- | --- | --- | --- | --- |
| Kimi K2 | 128k | $0.57 / $2.30 per MTok | agentic/coding oriented, but weaker coding category results than selected defaults | fallback only |
| GLM 4.5 | 164k | $0.60 / $2.20 per MTok | strong throughput, but not a clear default win on coding/tool-use reliability | fallback only |
| DeepSeek V3.1 | 164k | $0.21 / $0.79 per MTok | good price/perf, but less proven than the selected defaults for tool-heavy runs | cost-floor fallback |

Sources: [Kimi K2](https://openrouter.ai/moonshotai/kimi-k2), [GLM 4.5](https://openrouter.ai/z-ai/glm-4.5), [DeepSeek V3.1](https://openrouter.ai/deepseek/deepseek-chat-v3.1).

## Proposed default mapping v1

```yaml
version: research-v1
tier_mode: prefer
tiers:
  light:
    - google:gemini-2.5-flash
    - anthropic:claude-haiku-4.5
    - openrouter:deepseek/deepseek-chat-v3.1
  standard:
    - openai:gpt-5.1-codex
    - anthropic:claude-sonnet-4.6
    - google:gemini-2.5-pro
  heavy:
    - anthropic:claude-opus-4.8
    - openai:gpt-5.1-codex
    - google:gemini-2.5-pro
  frontier:
    - anthropic:claude-opus-4.8
    - google:gemini-2.5-pro
    - openai:gpt-5.1-codex
```

### Rationale by tier

- **light** — optimize for cheap, fast, high-context docs/review work. Flash is the best verified cost/perf fit; Haiku is the Anthropic fallback; DeepSeek is the cheapest fallback when cost dominates quality.
- **standard** — optimize for single-module code+tests and ordinary implementation slices. GPT-5.1-Codex is the strongest code-focused default; Sonnet 4.6 is the balanced Anthropic fallback; Gemini 2.5 Pro is the long-context backup.
- **heavy** — optimize for cross-module refactors, repair loops, and multi-file test coherence. Opus 4.8 is the top Anthropic candidate; GPT-5.1-Codex remains a strong code-centric fallback; Gemini 2.5 Pro is the best context-heavy backup.
- **frontier** — reserve for the hardest slices where a failed first pass is expensive. Opus 4.8 leads; Gemini 2.5 Pro is the context/multimodal alternate; GPT-5.1-Codex stays available when the task is still mostly code.

## Cost-per-slice estimates

Assumptions: **docs-only = 8k input / 2k output**, **single-module code+tests = 30k input / 6k output**, **cross-module = 90k input / 12k output**.

| Model | Docs-only | Single-module code+tests | Cross-module |
| --- | ---:| ---:| ---:|
| google:gemini-2.5-flash | $0.005 | $0.0165 | $0.0405 |
| anthropic:claude-haiku-4.5 | $0.018 | $0.060 | $0.150 |
| openrouter:deepseek/deepseek-chat-v3.1 | $0.0033 | $0.0110 | $0.0284 |
| openai:gpt-5.1-codex | $0.030 | $0.0975 | $0.2325 |
| anthropic:claude-sonnet-4.6 | $0.054 | $0.180 | $0.450 |
| google:gemini-2.5-pro | $0.040 | $0.132 | $0.324 |
| anthropic:claude-opus-4.8 | $0.090 | $0.300 | $0.750 |
| openrouter:moonshotai/kimi-k2 | $0.0092 | $0.0309 | $0.0789 |
| openrouter:z-ai/glm-4.5 | $0.0092 | $0.0312 | $0.0804 |

## When a model should move tiers

- **Up-tier** when a slice regularly needs more context than the current tier comfortably handles, or when repair loops and tool-use failures become the norm.
- **Down-tier** when a model is deprecated/retired, no longer clearly beats the cheaper tier on representative slices, or its context/feature posture regresses.
- **Move to frontier** when the slice spans multiple modules or repositories, needs sustained long-context synthesis, or benchmark/attempt-chain data shows that the heavy tier still fails too often.
- **Move to standard** when a task is still code/test-bearing but no longer needs frontier-grade reasoning or 1M-context synthesis.
- **Use benchmark data as the tie-breaker**: RON-29 attempt chains and RON-1 / BEI-24 benchmark runs should eventually overrule static research.

## Refresh cadence and update path

- Refresh this table **monthly** and immediately after any vendor lifecycle change, pricing change, or context-window change.
- Treat benchmark/attempt-chain results as the ground truth once enough data exists.
- When BEI-76 lands its formal mapping format, transplant this ordering into the shipped `model_routing.tiers` default table and record the mapping version in the resolved envelope metadata.
- Keep the current mapping version pinned in exported hints so future runs can explain which research snapshot resolved them.

## Ground-truth cross-check snapshot

Current Linear snapshot on 2026-06-28:
- **RON-29** — Todo / unstarted; no attempt-chain evidence yet.
- **RON-1** — Backlog; benchmark runner not yet producing results.
- **BEI-24** — Backlog; same benchmark gap on the Beislið side.

That means the ladder/benchmark data still cannot displace the static research ordering here.

## Evaluated but excluded from the default ordering

- **Anthropic Claude Opus 4.1 / Sonnet 4 / Haiku 3.5** — deprecated or retired; do not route new defaults there.
- **OpenAI GPT-5** — superseded by GPT-5.1 / GPT-5.1-Codex.
- **OpenAI GPT-5.5** — no confirmable current official model page in this pass.
- **OpenRouter Kimi K2** — useful agentic fallback, but weaker coding-category evidence and smaller context than the selected long-context defaults.
- **OpenRouter GLM 4.5** — competitive price/perf, but not a clear default win on tool-use/coding reliability.
- **OpenRouter DeepSeek V3.1** — very cheap and competent, but better as a cost-floor fallback than a primary default.

## Bottom line

If BEI-76 shipped today, the least-risk default table would be:

- `light` → Gemini 2.5 Flash first, Haiku 4.5 second, DeepSeek V3.1 third
- `standard` → GPT-5.1-Codex first, Sonnet 4.6 second, Gemini 2.5 Pro third
- `heavy` → Opus 4.8 first, GPT-5.1-Codex second, Gemini 2.5 Pro third
- `frontier` → Opus 4.8 first, Gemini 2.5 Pro second, GPT-5.1-Codex third

That keeps the cheap tier cheap, uses code-specialized models for code-heavy work, and reserves the most expensive models for the slices where failure costs the most.