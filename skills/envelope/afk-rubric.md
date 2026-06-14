# afk-rubric v1

Versioned AFK-eligibility rubric for execution envelopes. Step 2 judges every candidate slice against each criterion below and records the verdict plus its evidence inline in the draft envelope, together with `rubric_version: afk-rubric-v1`. A repo may override this document via the `beislid:envelope` block's `rubric_path` in workflow.md (see SKILL.md); whichever rubric is used, its version string is what gets recorded and exported.

A slice is AFK-eligible only when **every** criterion passes with evidence. Any criterion that cannot be evidenced in-session fails — the slice is auto-marked **demote-to-HITL** (Step 3 default stands).

## Criteria

Each criterion states what the authoring agent must check and what counts as evidence.

1. **Bounded file scope, explored in-session.** Every include path in the slice scope was listed or read in this session (`ls`, `glob`, or file reads), and the scope is a closed set — no "and wherever else this is used" tails. Evidence: the explored paths and how each was confirmed to exist.

2. **Every cited gate command probed to exist.** For each verification/gate command the envelope cites: probe the first word with `command -v <word>`, or for repo scripts probe presence with `test -f <path>` (plus interpreter availability). A command that fails its probe is an unverified claim. Evidence: the probe command and its result per cited gate.

3. **Dependencies resolved to real artifacts.** Every dependency (branch, fixture, tool, config, upstream slice output) resolves to something that demonstrably exists now or is produced by an earlier slice in the same bundle's dependency graph. Evidence: per dependency, the path/ref/graph edge that satisfies it.

4. **Mechanically verifiable success criteria.** Done-ness is decidable by running commands and reading exit codes/output — no "looks right", "feels complete", or human-judgment acceptance. Evidence: the exact verification commands and the observable pass condition for each.

5. **No design-bearing or product decisions inside the slice.** All decisions that shape architecture, public contracts, UX, or product behavior were made in this session and are written into the prompt's Design summary; the runner only executes. Evidence: an explicit statement that remaining choices are mechanical, or the list of decisions pre-resolved in the prompt.

6. **Reversible via git.** The slice's effects are confined to tracked workspace changes that a `git revert`/branch deletion undoes. No migrations against shared state, no external service mutations, no deletes outside the repo. Evidence: confirmation that allow/ask/deny lists permit no irreversible action.

## Recording the judgment

Per slice, record: `rubric_version`, per-criterion pass/fail with the evidence above, and the resulting eligibility (`afk` or `demote-to-HITL`). Unverifiable evidence is a fail, never a "probably fine".
