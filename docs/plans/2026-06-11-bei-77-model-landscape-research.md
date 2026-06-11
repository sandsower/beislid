# BEI-77 — Model landscape research for capability-tier mapping defaults

Research date: **2026-06-11**. Status: **research-v1, provisional** — this document is
format-agnostic by design. BEI-76 (envelope orchestrator) owns the shipped mapping-table
format and had not started when this research ran; the YAML block below is research
output, **not** an authoritative mapping table. When BEI-76 v1 lands, a follow-up PR
derives the versioned table from this document. Per-repo `workflow.md` overrides remain
authoritative over any default proposed here.

## 1. Methodology and sources

- Four provider-family sweeps (Anthropic, OpenAI, Google, open-weight) ran as parallel
  research agents over primary sources: provider pricing/model/deprecation documentation
  pages and official announcements, fetched directly.
- Every sweep was then adversarially re-verified by an independent agent instructed to
  refute each load-bearing claim (price per Mtok, context window, deprecation date,
  benchmark score) against primary sources and to hunt for missing models. 15 corrections
  surfaced and are folded in below; ~198 load-bearing claims were confirmed.
- A cost-modeling pass computed per-slice estimates (section 4); an arithmetic verifier
  recomputed all 29 rows with zero discrepancies.
- Benchmark figures are labeled by provenance: **(primary)** = provider's own
  announcement/model card; **(vendor)** = vendor-reported, no independent reproduction
  found; **(secondary)** = third-party tracker only. Scores from different scaffolds are
  not directly comparable — treat cross-provider deltas under ~3 points as noise.
- This landscape goes stale fast. Everything below is a snapshot of 2026-06-11.

## 2. Per-provider landscape

### Anthropic (reachable via the `claude_code` adapter)

| Model | $/Mtok in/out | Context | Agentic evidence | Lifecycle |
|---|---|---|---|---|
| `claude-fable-5` | 10 / 50 | 1M | SOTA claims incl. top FrontierCode at medium effort (primary); ~93.9–95% SWE-bench V (secondary, unverified) | GA 2026-06-09, no sunset |
| `claude-mythos-5` | 10 / 50 | 1M | Same model as Fable 5 | Restricted (Project Glasswing only) |
| `claude-opus-4-8` | 5 / 25 | 1M | 84% Online-Mind2Web, SOTA long-horizon agentic (primary); no SWE-bench V published | GA, retire ≥2027-05-28 |
| `claude-opus-4-7` | 5 / 25 | 1M | Superseded by 4.8 at same price (primary) | Legacy, retire ≥2027-04-16 |
| `claude-opus-4-6` | 5 / 25 | 1M | 80.84% SWE-bench V (primary) | Legacy, retire ≥2027-02-05 |
| `claude-sonnet-4-6` | 3 / 15 | 1M | 79.6% SWE-bench V, 59.1% Terminal-Bench 2.0 (primary) | GA, retire ≥2027-02-17 |
| `claude-haiku-4-5` | 1 / 5 | 200K | 73.3% SWE-bench V (primary) | GA, retire ≥2026-10-15 |
| `claude-opus-4-5` | 5 / 25 | 200K | ~80.9% SWE-bench V at launch (primary-era, approximate) | Legacy, retire ≥2026-11-24 |
| `claude-sonnet-4-5` | 3 / 15 | 200K | 77.2% SWE-bench V (primary) | Legacy, retire ≥2026-09-29 |

Notes: 1M context at standard pricing on Opus 4.8/4.7/4.6 and Sonnet 4.6 — no
long-context premium, which matters for cross-module slices. Fable 5 and Opus 4.7+ use a
new tokenizer (~30% more tokens for the same content — cost comparisons against older
models must re-baseline). Fable 5 requires 30-day retention (no ZDR) and can return
`stop_reason: refusal` with server-side fallback to Opus 4.8. Fast-mode variants exist
for Opus 4.6/4.7/4.8 at 2× pricing (correction from verification; treated as variants,
not separate candidates). Batch API −50%; cache reads ~0.1×. Lifecycle: ≥60 days notice
before retirement; dates are "not sooner than".

### OpenAI (reachable via the pi harness)

| Model | $/Mtok in/out | Context | Agentic evidence | Lifecycle |
|---|---|---|---|---|
| `gpt-5.5` | 5 / 30 (≤272K in); 10 / 45 above | 1.05M | 82.6% SWE-bench V, 82.7% Terminal-Bench 2.0 (primary) | GA 2026-04-23, consolidation target |
| `gpt-5.4` | 2.5 / 15 (≤272K in); 5 / 22.5 above | 1.05M | ~80% SWE-bench V (primary); 77.2% (independent, Vals.ai) | GA 2026-03-05 |
| `gpt-5.4-mini` | 0.75 / 4.5 | 400K | No published scores; named replacement for gpt-5.1-codex-mini (primary) | GA |
| `gpt-5.4-nano` | 0.2 / 1.25 | 400K | None — classification/extraction tier | GA |
| `gpt-5.3-codex` | 1.75 / 14 | 400K | ~80% SWE-bench V, ~77.3% Terminal-Bench 2.0 at release (primary/secondary mix) | GA, only surviving codex |
| `gpt-5.3-codex-spark` | unpublished | 128K | None published; >1000 tok/s | Preview, design partners only |

Notes: the long-context price tier on gpt-5.5/5.4 (correction from verification: prompts
>272K input bill at 2× in / 1.5× out) materially changes cross-module economics — see
section 4. Aggressive deprecation wave: gpt-5.x chat/codex lines shut down 2026-07-23
(incl. gpt-5.2-codex — corrected from 2026-10-23) and 2026-08-10, all consolidating onto
gpt-5.5 / gpt-5.4-mini. Cached input ≈0.1× across the family.

### Google (reachable via the pi harness)

| Model | $/Mtok in/out | Context | Agentic evidence | Lifecycle |
|---|---|---|---|---|
| `gemini-3.5-flash` | 1.5 / 9 | 1.05M | 76.2% Terminal-Bench 2.1, 83.6% MCP Atlas; "outperforms 3.1 Pro on coding/agentic" (primary); no SWE-bench V published | GA stable, May 2026 |
| `gemini-3.1-pro-preview` | 2 / 12 (≤200K); 4 / 18 above | 1.05M | 80.6% SWE-bench V, 68.5% Terminal-Bench 2.0 (primary model card) | **Preview**, no stable ID; 3.5 Pro imminent |
| `gemini-3-flash-preview` | 0.5 / 3 | 1.05M | 78% SWE-bench V (primary) | **Preview**; superseded by 3.5 Flash |
| `gemini-3.1-flash-lite` | 0.25 / 1.5 | 1.05M | None published | GA stable |
| `gemini-2.5-pro` / `-flash` / `-flash-lite` | 1.25/10 · 0.3/2.5 · 0.1/0.4 | 1.05M | 2.5-pro: 63.8% SWE-bench V (primary, custom scaffold) | **All shut down 2026-10-16** |

Notes: the entire 2.5 stable line dies 2026-10-16 — nothing should be tiered on it.
Google's strongest agentic-coding model is currently the GA *flash* (3.5 Flash); its pro
tier is preview-only with a 3.5 Pro launch announced as imminent. Batch −50% across the
line.

### Open-weight families (adapter reach varies; pricing = official first-party API unless noted)

| Model | $/Mtok in/out | Context | Agentic evidence | Status |
|---|---|---|---|---|
| `deepseek-v4-pro` | 0.435 / 0.87 | 1M | 80.6% SWE-bench V (vendor; tracked on llm-stats) | GA, MIT weights |
| `deepseek-v4-flash` | 0.14 / 0.28 | 1M | ~79% SWE-bench V (vendor; llm-stats lists 79.0% — corrected) | GA, MIT weights |
| `kimi-k2.6` (Moonshot) | 0.95 / 4 | 262K | 80.2% SWE-bench V, 66.7% Terminal-Bench 2.0 (vendor model card) | GA, modified-MIT weights |
| `glm-5.1` (Z.ai) | 1.4 / 4.4 | ~200K (unpinned) | 58.4 SWE-bench Pro (vendor); GLM-5 77.8% SWE-bench V (secondary) | GA, MIT weights |
| `MiniMax-M3` | 0.30 / 1.20 ≤512K (corrected — permanent 50% off) | 1M | 59.0 SWE-bench Pro (vendor); 80.5% SWE-bench V (secondary, llm-stats — corrected) | GA API; **weights NOT shipped as of 2026-06-11 (corrected) — API-only in practice** |
| `qwen3-coder-next` | 0.3 / 1.5 (tiered by request size) | 262K | 70.6–71.3% SWE-bench V across three scaffolds (vendor tech report) | GA, Apache 2.0 |
| `Qwen3.6-27B` | no first-party API price | 262K | 77.2% SWE-bench V (vendor model card) | GA, Apache 2.0; hosted/self-host only |
| `devstral-medium-latest` (Mistral) | 0.4 / 2 | 256K | 72.2% SWE-bench V (vendor) | GA, modified-MIT 123B |
| `devstral-small-latest` (Mistral) | 0.1 / 0.3 | 256K | 68.0% SWE-bench V (vendor) | GA, Apache 2.0 24B |
| `llama-5` (Meta) | no first-party API | — | 47.3% SWE-bench V (secondary, low confidence) | GA, community license |

Verification also surfaced two missing models, recorded for the watchlist (section 7):
Poolside Laguna XS.2 (Apache 2.0, 68.2% SWE-bench V) and NVIDIA Nemotron 3 Ultra/Super
(65–70.4% / 60.5% SWE-bench V). DeepSeek legacy IDs `deepseek-chat`/`deepseek-reasoner`
deprecate 2026-07-24; Moonshot has discontinued the whole K2-preview line.

## 3. Proposed tier → ordered-candidates mapping (research-v1, provisional)

Tier semantics anchor to slice shape: `light` ≈ docs-only/glue work, `standard` ≈
single-module code+tests, `heavy` ≈ cross-module changes and long-horizon runs,
`frontier` ≈ hardest work and the top of the RON-29 escalation ladder.

Ordering rationale, applied uniformly: (1) GA models only — previews and
restricted-availability models are excluded from defaults; (2) primary-source agentic
evidence outranks vendor-only claims; (3) the `claude_code` adapter is rondo's most
mature execution path, so Anthropic candidates lead where capability is comparable;
(4) candidates served only by vendors without a proven rondo/pi adapter path are
trailing entries, marked `adapter-unproven`, and are aspirational until an adapter
exists.

```yaml
# research-v1 (2026-06-11) — PROVISIONAL research output, not a BEI-76 mapping table.
# Portable aliases (haiku/sonnet/opus) per workflow-md-format; namespaced IDs otherwise.
mapping_version: research-v1
tiers:
  light:
    - model: haiku                     # claude-haiku-4-5 — $1/$5
      rationale: 73.3% SWE-bench V (primary), cheapest claude_code-adapter path;
        200K context caps very large slices.
    - model: openai:gpt-5.4-mini       # $0.75/$4.5
      rationale: no published agentic scores, but OpenAI's designated codex-mini
        replacement and pitched for subagents; cheapest big-three coding-credible tier.
    - model: deepseek:deepseek-v4-flash  # $0.14/$0.28 — adapter-unproven
      rationale: ~79% SWE-bench V (vendor, llm-stats-tracked) at ~1/10 the cost of
        haiku; trailing because vendor-only evidence and no proven adapter.
  standard:
    - model: sonnet                    # claude-sonnet-4-6 — $3/$15
      rationale: 79.6% SWE-bench V (primary), 1M context, no long-context premium,
        mature adapter; best-evidenced workhorse.
    - model: google:gemini-3.5-flash   # $1.5/$9
      rationale: GA stable, Google's strongest agentic coder (76.2% TB 2.1, primary);
        cheaper than sonnet, but no SWE-bench V published.
    - model: openai:gpt-5.3-codex      # $1.75/$14
      rationale: ~80% SWE-bench V, agent-harness-optimized, cheapest large coding
        model in OpenAI's lineup; sole codex survivor of the deprecation wave.
    - model: deepseek:deepseek-v4-pro  # $0.435/$0.87 — adapter-unproven
      rationale: 80.6% SWE-bench V (vendor) at ~1/8 sonnet cost; trailing on
        evidence provenance and adapter status.
  heavy:
    - model: opus                      # claude-opus-4-8 — $5/$25
      rationale: SOTA long-horizon agentic execution (primary), 1M context at flat
        pricing — no long-context premium on cross-module slices.
    - model: openai:gpt-5.4            # $2.5/$15 short-context
      rationale: ~80% SWE-bench V (primary), 77.2% independent; cheaper than opus
        until prompts cross 272K input, where 2x/1.5x premium applies.
    - model: google:gemini-3.5-flash   # $1.5/$9
      rationale: degradation candidate; strong agentic scores and flat 1M-context
        pricing, materially cheaper for long cross-module runs.
  frontier:
    - model: anthropic:claude-fable-5  # $10/$50
      rationale: Anthropic's strongest GA model (SOTA claims, primary; ~94% SWE-bench V
        secondary), first-party adapter; new tokenizer inflates effective cost ~30%.
    - model: openai:gpt-5.5            # $5/$30 short-context
      rationale: best primary-source-verified agentic scores in this sweep (82.6%
        SWE-bench V / 82.7% TB 2.0); long-context premium erodes its price advantage
        on cross-module work (see section 4).
    - model: opus                      # claude-opus-4-8 — degradation candidate
      rationale: keeps frontier-tier envelopes executable when Fable 5 is
        unavailable; also Fable 5's own server-side classifier fallback.
```

`gemini-3.1-pro-preview` is the strongest Google model on SWE-bench V (80.6%, primary)
but is excluded from defaults by the GA-only rule; expect Gemini 3.5 Pro to enter
`heavy`/`frontier` candidacy at the next refresh.

## 4. Cost-per-slice estimates

Token-volume assumptions (verified arithmetic; output held at ~5% of input because
agentic cost is dominated by context re-sends): **docs-only** 1.0 Mtok in / 0.05 out ·
**single-module code+tests** 6.0 / 0.3 · **cross-module** 20.0 / 1.0. No caching
discount applied — these are conservative uncached upper bounds; real costs with prompt
caching are substantially lower everywhere. Long-context premiums applied to the
cross-module shape only (gpt-5.5/5.4: prompts assumed to cross 272K input there).

| Model (tier) | docs-only | single-module | cross-module |
|---|---|---|---|
| `claude-fable-5` (frontier) | $12.50 | $75.00 | $250.00 |
| `gpt-5.5` (frontier) | $6.50 | $39.00 | $245.00 |
| `claude-opus-4-8` (heavy/frontier) | $6.25 | $37.50 | $125.00 |
| `gpt-5.4` (heavy) | $3.25 | $19.50 | $122.50 |
| `claude-sonnet-4-6` (standard) | $3.75 | $22.50 | $75.00 |
| `gpt-5.3-codex` (standard) | $2.45 | $14.70 | $49.00 |
| `gemini-3.5-flash` (standard/heavy) | $1.95 | $11.70 | $39.00 |
| `claude-haiku-4-5` (light) | $1.25 | $7.50 | $25.00 |
| `gpt-5.4-mini` (light) | $0.97 | $5.85 | $19.50 |
| `deepseek-v4-pro` (standard, trailing) | $0.48 | $2.87 | $9.57 |
| `deepseek-v4-flash` (light, trailing) | $0.15 | $0.92 | $3.08 |

Two structural observations: gpt-5.5's headline price halves Fable 5's, but the >272K
long-context tier brings its cross-module cost to near parity ($245 vs $250); and
Anthropic's flat 1M-context pricing is a real advantage specifically on the heavy tier,
where opus beats gpt-5.4 once prompts run long. Open-weight candidates are 8–25× cheaper
than same-tier majors — the strongest argument for building pi-harness adapter coverage.

## 5. Tier-movement criteria

A model moves between tiers (or in/out of candidacy) when, at a refresh:

1. **GA gate** — only GA, unrestricted models may appear in defaults. Preview, design-
   partner, or restricted-availability models are excluded regardless of scores; a
   model entering GA becomes eligible at the next refresh.
2. **Deprecation exit** — an announced shutdown/retirement date within two refresh
   cycles (≈6 months) removes the model from defaults at the next refresh; the vendor's
   named replacement is auto-evaluated for the vacated slot.
3. **Benchmark band** — a model's best primary-source (or independently reproduced)
   SWE-bench-Verified-class score must sit within 5 points of its tier's current median
   to stay; ≥5 points above the next tier up's median is promotion evidence, ≥5 below
   its own tier's median is demotion evidence. Vendor-only scores qualify a model for
   trailing candidacy at most.
4. **Cost band** — a pricing change that moves a model's cross-module cost estimate
   past 2× (or under 0.5×) of its tier's median cost triggers re-tiering review; cost
   alone never promotes a model above its capability evidence.
5. **Ground-truth override (RON-29 / RON-1 / BEI-24)** — once ≥30 envelope runs per
   model-tier pair exist: an escalation rate (RON-29 attempt chains escalating off the
   model) above 25% on tier-typical slices is demotion evidence; a cheaper candidate
   completing ≥80% of escalated-to-it work is promotion evidence. Internal benchmark
   results (RON-1/BEI-24) at n≥30 override public benchmark scores wherever they
   disagree. **No data exists yet for any of these — hook points only.**
6. **Adapter status** — `adapter-unproven` candidates become full candidates only when
   a rondo adapter executes ≥10 successful envelope runs against them; they are
   removed if no adapter materializes within two refresh cycles.

## 6. Refresh cadence and update path

- **Scheduled refresh: quarterly** (next: 2026-09, then 2026-12). Each refresh re-runs
  the sweep+verify methodology of section 1, applies section 5 criteria, and bumps the
  mapping version.
- **Event-driven refresh** between quarters when any of: a default candidate announces
  deprecation; a default candidate's pricing changes >25%; a major release plausibly
  alters tier ordering (e.g. Gemini 3.5 Pro GA). Event refreshes may touch only the
  affected tier entries (minor version bump).
- **Versioning and update path** (to align with BEI-76 when it lands): the shipped
  mapping table is versioned (`mapping-v<N>`, with this research as its provenance
  trail); envelopes record which mapping version resolved their hints, so attempt
  chains remain interpretable across refreshes. Every refresh lands as a PR with a
  changelog row: version, date, what moved, which criterion (section 5) drove each
  move. As RON-29/RON-1/BEI-24 data accumulates past the n≥30 thresholds, criterion 5
  progressively replaces the static-research criteria 3–4 as the primary mover —
  benchmark-data-driven mappings are the end state; this document is the bootstrap.

## 7. Models evaluated and excluded

In defaults (12 candidate slots, 10 distinct models): see section 3.

| Excluded model | Reason |
|---|---|
| `claude-mythos-5` | Restricted availability (Project Glasswing only); same model as Fable 5 |
| `claude-opus-4-7`, `claude-opus-4-6`, `claude-opus-4-5` | Superseded by Opus 4.8 at identical pricing; no selection reason |
| `claude-sonnet-4-5` | Superseded by Sonnet 4.6 at identical pricing; 200K context |
| `gpt-5.4-nano` | Not an agentic-coding model (classification/extraction tier) |
| `gpt-5.3-codex-spark` | Preview, design partners only, no public API/pricing (criterion 1) |
| Deprecated gpt-5.x chat/codex line | Shutdowns 2026-07-23 / 2026-08-10 (criterion 2) |
| `gemini-3.1-pro-preview` | Preview only (criterion 1) despite best Google SWE-bench V; revisit at 3.5 Pro GA |
| `gemini-3-flash-preview` | Preview (criterion 1); superseded by GA 3.5 Flash |
| `gemini-3.1-flash-lite` | No agentic evidence at all (criterion 3) |
| Gemini 2.5 line (pro/flash/flash-lite) | Shutdown announced 2026-10-16 (criterion 2) |
| `MiniMax-M3` | Promised open weights not shipped as of 2026-06-11 (API-only); vendor-only benchmarks; new-vendor risk. Watchlist — 80.5% SWE-bench V (secondary) at $0.30/$1.20 is compelling if it firms up |
| `glm-5.1` | Vendor-only benchmarks; context window unpinned on primary sources; recent price increase. Watchlist |
| `kimi-k2.6` | Strong vendor model-card scores (80.2% SWE-bench V) but vendor-only evidence, 262K context, no adapter; narrowly lost the trailing-candidate slots to DeepSeek on price+context. Watchlist |
| `qwen3-coder-next` | 70.6–71.3% SWE-bench V sits below the standard-tier band; size-tiered pricing complicates cost modeling. Watchlist for light tier |
| `Qwen3.6-27B` | No first-party API pricing (hosted/self-host only); strong self-host option if rondo grows a local adapter |
| `devstral-medium-latest` / `devstral-small-latest` | 72.2% / 68.0% SWE-bench V (vendor) below tier bands; small is the best local/consumer-hardware option |
| `llama-5` | 47.3% SWE-bench V (secondary) — far below every tier band; no first-party API |
| Poolside Laguna XS.2 | Surfaced by verification as missing; 68.2% SWE-bench V, below bands. Watchlist for local/light |
| NVIDIA Nemotron 3 Ultra / Super | Surfaced by verification as missing; 65–70.4% / 60.5% SWE-bench V, below bands |

## 8. Provenance

Produced by a 10-agent research workflow (4 provider sweeps → 4 adversarial verifiers →
cost model → arithmetic verifier), 2026-06-11, for Linear BEI-77. 15 verifier
corrections applied; cost table verified to 0% deviation. Source URLs for every
load-bearing claim live in the workflow transcript; headline sources: platform.claude.com
model/pricing/deprecation docs, anthropic.com announcements, developers.openai.com
pricing/models/deprecations, ai.google.dev pricing/deprecations, blog.google and
DeepMind model cards, vendor model cards on HuggingFace, api-docs.deepseek.com,
platform.minimax.io pricing, mistral.ai announcements, llm-stats.com leaderboards
(secondary).
