# Beislið skills

This is the full skill catalog. For first-run guidance, start with [How to use Beislið](./how-to-use.md). For lifecycle diagrams, see [Workflows](./workflows.md).

## Plan

- `kickoff`: fetch a ticket and route to the right workflow; may derive a Work Contract and write a configured context checkpoint.
- `spec`: brainstorm and shape lightweight product specs; may finalize a Work Contract and write approved spec artifacts when configured.
- `break-spec`: break large specs into vertical implementation phases.
- `blueprint`: design before implementation from clear requirements or an approved Work Contract; may write approved design artifacts when configured.
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
| `break-spec`    | Product decomposition       | A spec or Work Contract is classified as `multi_slice`, or `project` boundaries are approved for slicing                  | `blueprint` for one phase                                     |
| `kickoff`       | Ticket router               | Starting work from an existing ticket branch; reads `<repo>/.beislid/workflow.md`; may derive a Work Contract and write configured context checkpoints | `spec`, `break-spec`, or `blueprint`                          |
| `blueprint`     | Implementation design gate  | Desired behavior or an approved Work Contract is known; code approach is not; runs configured design artifact actions after approval | `implement`                                                   |
| `implement`     | Execution planning          | Implementation design is approved; may consume approved execution envelopes and write configured implementation-plan checkpoints | code changes + `verify`                                       |
| `verify`        | Evidence gate               | Before claiming done/fixed/passing                                                                                        | commit/submit                                                   |
| `debug`         | Debugging gate              | Bug, failing test, or unexpected behavior                                                                                 | fix + `verify`                                                |
| `review`        | Review primitive            | Local or supplied diff needs first-pass findings and a readiness verdict                                                  | caller decides: fix, post, loop, or submit                      |
| `fresh-eyes`    | Review primitive            | Post-fix whole diff needs a final consistency/drift pass                                                                  | caller decides: fix, accept risk, or submit                     |
| `rinse`         | Review orchestrator         | You want an approved review/fix/verify loop                                                                               | `fresh-eyes` or `ready-for-review`                                     |
| `pr-patrol`     | Inbound PR review           | You are reviewing someone else's PR and may post approved comments                                                        | posted review or draft comments                               |
| `ready-for-review`       | Review handoff flow               | Branch is ready for a new PR or an existing PR update; reads `<repo>/.beislid/workflow.md` and probes capabilities lazily | new PR or pushed update                                       |
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

- `credential_guard` hook: blocks bash commands that dump secrets. Claude Code-specific; the skills themselves are portable markdown. See [Credential guard](./credential-guard.md).
- Beislið Pi extension: managed slash-command wrappers for the skill surface, plus automatic fresh-session handoff from checkpoint pointers when configured. Portable skills and Claude/manual fallback remain unchanged.
