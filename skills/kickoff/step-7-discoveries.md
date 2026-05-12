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

1. `probe(domain_expert.agent)` if not already ok in this run.
2. `probe(knowledge_store.path)` as a path capability.
3. If both ok, spawn the domain expert to record discoveries into the knowledge store.

If a probe is skipped for this session, exclude it from cache write-back.

## Exit

Print the Step 7 exit one-liner. Required outputs: discovery status (`recorded` or `skipped`), reason, and any durable notes recorded.

## Tripwires

- `knowledge_store.path` alone is not useful.
- Discovery recording is best-effort and must not start implementation.
