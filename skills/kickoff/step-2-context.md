# kickoff step 2 context v1

Authoritative JIT protocol for kickoff Step 2. Load after Step 1 has ticket context.

## Purpose

Explore the codebase before design. Gather likely files, patterns, tests, docs, and optional domain context.

## Protocol

Print the Step 2 entry one-liner from `kickoff-templates.md`.

### 2a. Codebase exploration

If `explore.skill` is configured, `probe(explore.skill)` as a `skill` capability before exploration. `explore.mode` must be `replace` or `enhance`; missing mode defaults to `enhance`.

- `replace`: invoke the skill instead of default exploration. It must return likely files/modules, patterns, tests/docs, and uncertainties. If the skill probe/invocation fails, prompt retry / fall back to default exploration for this session / abort.
- `enhance`: run default exploration, then invoke the skill and merge its findings. If the skill fails, note it and continue with default findings.

When no replacement skill is active, explore the repo before designing. Find likely files, existing patterns, tests, docs, and similar implementations. Use `rg`, `find`, and Read. Do not assume structure from filenames alone.

Record concise evidence:

- likely files or modules to touch
- similar implementations to follow
- tests that cover the area or should be added
- docs/config that may need updates
- open uncertainties that should go to spec or blueprint
- explore mode (`default`, `replace`, or `enhance`) and skill status when configured

### 2b. Domain context

`domain_expert.agent` remains useful for read-only context and is separate from `explore.skill`. If configured and the work is not a pure UI/styling change, formatting-only refactor, or simple dependency bump:

1. `probe(domain_expert.agent)` as a `subagent` capability.
2. If ok, spawn the configured subagent with the ticket summary and codebase findings.
3. If skipped or unavailable, note why and continue with local context.

If only `knowledge_store.path` is configured, print the paired-half warning from `kickoff-templates.md`; it is not useful without a domain expert.

## Exit

Print concise context findings and the Step 2 exit one-liner. Required outputs: explore mode/status, relevant file count/list, patterns to follow, tests/docs candidates, domain context status, and open uncertainties.

## Tripwires

- No design before exploration or approved replacement exploration.
- `replace` mode cannot continue blind if the skill fails; use retry, default-exploration fallback, or abort.
- Do not block kickoff solely because optional enhance/domain context is unavailable.
