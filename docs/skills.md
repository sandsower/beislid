# Beislið skills

This is the full skill catalog. For first-run guidance, start with [How to use Beislið](./how-to-use.md). For lifecycle diagrams, see [Workflows](./workflows.md). For guidance on writing your own portable custom skills, see [Skill authoring](./skill-authoring.md).

Lifecycle artifact templates are standardized in [`.beislid/artifact-templates.md`](../.beislid/artifact-templates.md): spec, blueprint, implementation plan, verification report, review report, fresh-eyes report, ship summary, and feedback response log. Skills default to local/chat artifacts for planning/proof/review and public ticket/PR summaries only when a workflow or orchestrator owns posting.

## Plan

- `kickoff`: fetch a ticket and route to the right workflow; may derive a Work Contract and write a configured context checkpoint.
- `spec`: brainstorm and shape lightweight product specs; may finalize a Work Contract, write approved spec artifacts when configured, and optionally post the approved spec body back into the tracker body.
- `break-spec`: break large specs into vertical implementation phases.
- `blueprint`: design before implementation from clear requirements or an approved Work Contract; may write approved design artifacts when configured.
- `envelope`: author, approve, and export execution envelopes for AFK slices as validated `.beislid/exports/` bundles; explicit trigger only. Re-feeding a manifest with pause/review feedback self-detects revision mode and re-exports a superseding version in place.
- `poke-holes`: adversarial plan stress-test.

## Execute

- `implement`: TDD-first file-level implementation plan; may consume an approved `execution-envelope-v0` autonomy boundary for an agent or external runner and write a configured pre-code checkpoint.
- `debug`: no fix without root cause.
- `handoff`: paste-ready context packet for another agent/session/worktree.

## Check

- `verify`: no success claims without evidence.
- `review`: side-effect-free local/supplied diff review with a readiness verdict.
- `fresh-eyes`: side-effect-free final whole-diff pass for consistency and drift.
- `rinse`: review/fix/verify loop around the `review` contract.
- `pr-patrol`: inbound PR review with approved-only comment posting.
- `show-me`: manually create a polished local HTML evidence/explanation deck.

## Deliver

- `walk-the-diff`: interactive walkthrough of your own diff for a human reviewer.
- `ready-for-review`: review-ready PR flow driven by `workflow.md`; runs `review` and the configured final check before new PR creation.
- `review-response`: handle PR/QA feedback after someone reviews or tests your work.
- `babysit`: goal-backed PR babysitting loop that keeps using configured review-response, gates, and optional closeout automation until the PR is green or blocked. Claude includes `/goal`; Pi requires `pi-goal`.

## Manage

- `setup`: configure `.beislid/workflow.md` interactively or run `setup update` for installed Beislið updates.
- `doctor`: audit `.beislid/workflow.md` and probe each configured capability.
- `retro`: review run/session evidence and recommend workflow improvements; hands accepted config changes to `setup`.

## Skill reference

| Skill           | Category                    | Use when                                                                                                                  | Usually followed by                                           |
| --------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `spec`          | Product shaping             | Brainstorming, vague tickets, lightweight PRD/spec or Work Contract writing; runs configured spec artifact actions after approval | `break-spec` or `blueprint`                                   |
| `break-spec`    | Product decomposition       | A spec or Work Contract is classified as `multi_slice`, or `project` boundaries are approved for slicing; runs configured structure artifact actions after approval | `blueprint` for one phase                                     |
| `kickoff`       | Ticket router               | Starting work from an existing ticket branch; reads `<repo>/.beislid/workflow.md`; may derive a Work Contract and write configured context checkpoints | `spec`, `break-spec`, or `blueprint`                          |
| `blueprint`     | Implementation design gate  | Desired behavior or an approved Work Contract is known; code approach is not; runs configured design artifact actions after approval | `implement`                                                   |
| `implement`     | Execution planning          | Implementation design is approved; may consume approved execution envelopes and write configured implementation-plan checkpoints | code changes + `verify`                                       |
| `envelope`      | AFK export flow             | Explicitly invoked to author/approve/export execution envelopes for AFK slices in a standalone session; fail-closed export validated by `beislid export validate` | external runner execution (e.g. `rondo run-once`)             |
| `verify`        | Evidence gate               | Before claiming done/fixed/passing                                                                                        | commit/submit                                                   |
| `debug`         | Debugging gate              | Bug, failing test, or unexpected behavior                                                                                 | fix + `verify`                                                |
| `review`        | Review primitive            | Local or supplied diff needs first-pass findings and a readiness verdict                                                  | caller decides: fix, post, loop, or submit                      |
| `fresh-eyes`    | Review primitive            | Post-fix whole diff needs a final consistency/drift pass                                                                  | caller decides: fix, accept risk, or submit                     |
| `rinse`         | Review orchestrator         | You want an approved review/fix/verify loop                                                                               | `fresh-eyes` or `ready-for-review`                                     |
| `pr-patrol`     | Inbound PR review           | You are reviewing someone else's PR and may post approved comments                                                        | posted review or draft comments                               |
| `ready-for-review`       | Review handoff flow               | Branch is ready for a new PR or an existing PR update; reads `<repo>/.beislid/workflow.md`, probes capabilities lazily, and can summarize configured ship-time planning artifacts | new PR or pushed update                                       |
| `review-response`    | Feedback loop               | PR review or QA feedback needs handling from workflow.md-configured sources                                               | push/reply                                                    |
| `babysit`       | PR babysitting flow         | Current PR should be monitored and advanced through configured review-response/gates until green or configured closeout; requires `/goal` support | green/merged PR or blocked handoff                            |
| `poke-holes`    | Pressure tool               | You want a design or plan challenged                                                                                      | revised design/plan                                           |
| `walk-the-diff` | Review walkthrough          | You want to tour local changes interactively                                                                              | feedback doc                                                  |
| `handoff`       | Parallel work utility       | You want to hand a scoped slice to another agent/session/worktree                                                         | paste into the receiving session                              |
| `show-me`       | Visual evidence/explanation | You want a local HTML deck for proof, review, demos, docs, or understanding                                               | local `index.html` artifact                                   |
| `setup`         | Project config / updates    | First-time wiring of `workflow.md`, changing config sections, or running `setup update` for installed Beislið updates     | config writes or installer update output                      |
| `doctor`        | Config audit                | You edited `workflow.md` or want a capability check before running orchestrators                                          | refreshed probe cache plus prose audit                        |
| `retro`         | Workflow tune-up            | You want post-run/session recommendations for workflow defaults, gates, policies, checkpoints, or handoffs                | `setup`, `doctor`, or no action                               |

## Optional integrations

- Lavish visual surfaces: optional supplemental HTML review/planning surfaces for workflows such as `spec`, conservative `blueprint` design comparisons/diagrams, conservative `poke-holes` decision trees/tradeoffs, and post-render `show-me` deck inspection when a repo configures `beislid:visual_surfaces`. Markdown/chat artifacts and Show Me deck directories remain canonical. Use `beislid plugin enable lavish`, `beislid plugin status lavish`, and an optional pinned `--command` to manage local plugin state; missing/disabled state, missing `npx`, failed deep checks, declined prompts, runtime failures, unknown typed actions, malformed payloads, and freeform-only feedback fall back to Markdown/chat or the portable deck result. `.lavish/` wrappers follow `artifact_retention` and should stay ignored unless explicit docs/example publication is intended. See [Configuration: Visual surfaces](./configuration.md#visual-surfaces).
- `credential_guard` hook: blocks bash commands that dump secrets. Claude Code-specific; the skills themselves are portable markdown. See [Credential guard](./credential-guard.md).
- Beislið Pi extension: managed slash-command wrappers for the skill surface, plus automatic fresh-session handoff from checkpoint pointers when configured. Portable skills and Claude/manual fallback remain unchanged.
