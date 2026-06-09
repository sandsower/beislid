# Show Me

`show-me` creates a local HTML portfolio/deck when terminal output is the wrong medium.

Use it to prove, explain, review, demo, or document something visually:

- verification evidence for a change
- code walkthroughs with diffs and rationale
- UI demos with screenshots, videos, and GIFs
- CLI demos with command logs or recordings
- documentation build-up from source material
- subsystem understanding with diagrams, tables, and citations
- review artifacts for humans who need to inspect evidence later

The skill is manual in v1. Existing workflows may suggest it, but `verify`, `ready-for-review`, and review flows do not run it automatically.

## Invocation examples

```text
/skill:show-me
show-me this branch
make a proof deck for this change
make an HTML deck explaining this subsystem
visualize this as HTML
create a walkthrough deck for the diff
review this visually
show me this works
```

If the request clearly asks to generate a deck, the agent should inspect the target and build one. If the request is ambiguous, the agent should classify the intended mode and ask before generating.

## Modes and presentation

`show-me` chooses the report shape from the subject:

| Mode | Use when |
|---|---|
| `verification` | Claims need proof through commands, media, or logs |
| `review` | Work or material needs a visual inspection artifact |
| `code-walkthrough` | A diff or implementation needs explanation and rationale |
| `ui-demo` | UI behavior is better shown with screenshots/video/GIFs |
| `cli-demo` | Command behavior needs logs, transcripts, or recordings |
| `docs` | Documentation needs rendered output, structure, and validation evidence |
| `understanding` | A subsystem/topic needs visual explanation from sourced facts |
| `mixed` | More than one mode applies |

The optional `presentation` field controls rendering style:

| Presentation | Default use |
|---|---|
| `visual-deck` | `understanding` + `EXPLANATORY`; visual decision decks with cards, comparisons, flow-style sections, and checklist framing |
| `evidence-deck` | `verification`, `cli-demo`, and `ui-demo`; evidence-first decks with logs/media/provenance emphasized |
| `report` | `docs`, `review`, `code-walkthrough`, and mixed reports unless explicitly set |

When `presentation` is omitted, the renderer infers it from `mode` and `status`.

## Output location

Default:

```text
${BEISLID_STATE_DIR:-~/.local/state/beislid}/show-me/<repo>/<timestamp>/
```

Repo-local output is allowed only when explicitly requested or configured:

```text
.beislid/show-me/<timestamp>/
```

Generated decks are local artifacts and should not be committed in v1. Current rendering assumes online access for CDN presentation libraries (`marked`, DOMPurify, Mermaid, Highlight.js); the source JSON, logs, and copied media stay local in the deck directory, and Markdown source remains visible as a fallback if libraries fail to load.

## Artifact structure

A deck/report directory contains the local source and evidence bundle:

```text
show-me/<repo>/<timestamp>/
  index.html
  show-me.json
  manifest.json
  assets/
    images/
    videos/
    gifs/
    diagrams/
  logs/
    commands/
```

- `index.html` is the polished human-readable artifact.
- `show-me.json` is the structured source document.
- `manifest.json` records provenance and run metadata.
- `assets/` stores copied or captured media.
- `logs/` stores full command logs and transcripts.

## Status values

A `show-me` deck can succeed, fail, or explain without a pass/fail claim:

- `PASS` — evidence supports the stated claim
- `FAIL` — evidence contradicts the claim or a check failed
- `INCOMPLETE` — some required evidence is missing
- `NOT SHOWN` — a claim was not demonstrated
- `NEEDS CAPTURE` — media/evidence tooling was unavailable or capture was deferred
- `EXPLANATORY` — understanding/documentation deck, not pass/fail verification
- `CONFLICTING` — sources disagree or evidence points in different directions
- `LOW_CONFIDENCE` — explanation is plausible but source coverage is weak

Failure decks are valid. If evidence fails, the deck should show the failure clearly and include suggested next checks.

## Evidence rules

Command evidence should include:

- command
- cwd
- timestamp
- exit status
- relevant stdout/stderr or a linked full log

Media evidence should include:

- source path or capture method
- copied asset path
- type
- caption
- hash when practical
- media sensitivity warning if the content may contain private data

Understanding decks should distinguish:

- sourced facts
- interpretation
- inferred rationale
- open questions

Explanatory understanding decks should prefer visual structures over prose-heavy sections: cards for concepts, comparison cards for options, flow-style diagrams for relationships, saved-data panels for backend behavior, decision trees for unresolved choices, and checklist cards for PM/reviewer decisions.

If capture tooling is missing or a capture fails, add a `NEEDS_CAPTURE` block instead of implying evidence exists.

## Example walkthrough: Show Me in Action

A generated example deck is committed at [`docs/show-me-example/index.html`](./show-me-example/index.html).

It demonstrates the intended `show-me` experience:

- `understanding` + `EXPLANATORY` rendering as a `visual-deck`
- card/comparison layout from ordinary markdown and table blocks
- a real command evidence block from `python3 scripts/validate_skills.py`
- an honest `NEEDS_CAPTURE` block for evidence not included in the demo
- provenance at the bottom of the deck
- a final “Recorded walkthrough” section containing a human-paced browser recording of the deck itself

The example directory includes the rendered HTML, source `show-me.json`, manifest, command log, and copied walkthrough video asset so it can be opened directly from the repository docs.

Generated decks are still local artifacts by default. This checked-in example is intentional documentation; normal `show-me` output should not be committed unless a workflow explicitly asks for a docs/example artifact. New renders also support Mermaid rendering from markdown fences or `diagram` source blocks and line-colored diffs through CDN presentation libraries; the committed example has not been regenerated for those renderer features yet.

## Privacy and redaction

`show-me` should apply best-effort redaction to text logs, JSON, and rendered HTML. Redactions should be noted in provenance.

Screenshots, videos, and GIFs may contain sensitive data. Treat them as local/private unless explicitly reviewed for sharing. The skill should warn about media sensitivity and must not claim media redaction unless a real redaction tool was used.

## Pi tooling

The portable skill works without Pi-specific tooling by writing files manually. In Pi, Beislið's managed command extension routes `/show-me` to this portable skill like the rest of the skill surface.

Older Beislið builds included a separate Show Me Pi deck-builder extension. That extension is no longer packaged by default; keep using the portable skill workflow unless a future package reintroduces dedicated deck-builder tools.

Window/screen capture, terminal recording, video/GIF conversion helpers, and richer capture automation are planned for later phases.
