# kickoff step 7 discoveries v1

Authoritative JIT protocol for kickoff Step 7. Load after blueprint approval and before ticket update.

## Purpose

Record durable domain discoveries when configured and useful.

## Protocol

Print the Step 7 entry one-liner from `kickoff-templates.md`.

Recording requires both `domain_expert.agent` and `knowledge_store.path`.

Skip when:

- either half is missing; print the paired-half note
- no new durable domain knowledge surfaced
- the change is pure UI/styling, formatting-only, dependency-only, or straightforward bug fix

If both halves are configured and recording is useful:

1. Reuse `domain_expert_resolution` from Step 2 when it is already `subagent` or `skill`.
2. Otherwise resolve `domain_expert.agent` the same way Step 2 does: probe as a `subagent` first; only when that returns `failed` with `probe_supported: false` because the host has no subagent mechanism, fall back to probing the same configured name as a `skill` capability.
3. `probe(knowledge_store.path)` as a path capability.
4. If `knowledge_store.path` is ok and the domain expert resolved as `subagent`, spawn the domain expert with the approved blueprint, implementation decisions, discovered terminology, and target knowledge-store path.
5. If `knowledge_store.path` is ok and the domain expert resolved as `skill`, invoke the skill inline in the current conversation with the same context and target knowledge-store path. Do not spawn a subagent for skill-resolved domain experts.

If a probe is skipped for this session, exclude it from cache write-back. If subagent resolution failed only because the host has no subagent mechanism but skill resolution succeeded, report the successful skill-backed resolution for this run and suppress the host-limit subagent failure from write-back. Do not write the skill-fallback success as the generic cached `domain_expert.agent` result; future runs must still start with the subagent-first resolution path.

## Exit

Print the Step 7 exit one-liner. Required outputs: discovery status (`recorded` or `skipped`), reason, and any durable notes recorded.

## Tripwires

- `knowledge_store.path` alone is not useful.
- Discovery recording is best-effort and must not start implementation.
- A host without subagent support is not by itself a reason to skip when `domain_expert.agent` resolves to an installed skill.
