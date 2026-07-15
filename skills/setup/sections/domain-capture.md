# setup section domain-capture v1

In verbose mode, emit `✓ setup/section-domain-capture v1 loaded` immediately after reading this file.

## Domain capture

Configure `domain_expert.agent` together with `knowledge_store.path`.
Ask for the domain expert name, then a repo-relative knowledge-store path.
Explain that kickoff resolves the expert as a subagent first and may fall back to an installed skill with the same name when the host has no subagent mechanism.
The pair is incomplete when either value is absent, so add, change, or remove them together unless the user explicitly accepts the existing half-pair behavior.
