---
name: show-me
description: "Use when the user asks for a visual HTML evidence/explanation artifact: 'show-me', 'show me this', 'make a proof deck', 'make an HTML deck', 'visualize this as HTML', 'this would be better as slides', 'make this visual', 'create a walkthrough deck', 'document this visually', or 'review this visually'. Manual/user-requested only in v1. Produces a polished local HTML portfolio/deck with evidence, media, logs, provenance, and clear missing-evidence markers."
---

# Show Me

Don't tell me. Show me.

`show-me` turns verification, review, explanation, documentation, demos, or subsystem understanding into a polished local HTML portfolio/deck when chat or terminal output is the wrong medium.

Use this for:
- proving a change works with evidence
- walking through code or architecture visually
- reviewing a diff, subsystem, or document set
- explaining a workflow, data flow, or decision tree
- building visual documentation from sourced facts
- showing UI, CLI, browser, or native-app behavior with media and logs

Do not use this for:
- automatic verification inside `verify`, `ready-for-review`, or other flows in v1
- making Lavish a required dependency or replacement renderer
- committing generated decks or `.lavish/` wrappers unless a workflow explicitly allows it
- hiding failed checks behind a polished report
- generating unsourced explanations that look authoritative

<HARD-GATE>
`show-me` is manual/user-requested in v1. Do not auto-run it from another Beislið skill. If another workflow thinks a visual deck would help, suggest it and wait for the user to ask.
</HARD-GATE>

Optional Lavish routing: after the canonical deck is created/rendered, apply `beislid:visual_surfaces` only when repo config exists and the effective `show-me` mode is active. Load the canonical `.beislid/visual-surface-protocol.md`; project installs may also expose a skill-local copy, but it must mirror the canonical file exactly and the canonical file wins on conflict. The protocol defines Show Me deck routing, `suggest`/`prompt`/`auto`, fallback, and `artifact_retention` semantics. The rendered `index.html`, `show-me.json`, and evidence bundle remain canonical and portable. Lavish may inspect them or use a supplemental wrapper under `.lavish/show-me/`, but disabled plugin state, missing command binaries, unavailable `npx`, declined prompts, command/editor failures, and freeform-only feedback are non-fatal fallbacks to the normal deck result.

## Output modes

Classify the deck before gathering evidence. Use one mode, or `mixed` when multiple apply. Also choose or infer a presentation: `visual-deck` for explanatory understanding decks, `evidence-deck` for proof/demo decks, and `report` for review/docs/code walkthroughs.

- `verification` — prove claims with command/media evidence
- `review` — inspect work or materials visually
- `code-walkthrough` — explain diffs, file roles, tests, risks, and rationale
- `ui-demo` — show UI behavior through screenshots, videos, GIFs, and browser evidence
- `cli-demo` — show command behavior through logs, transcripts, or terminal recordings
- `docs` — visualize rendered docs, validation output, and documentation structure
- `understanding` — explain a subsystem/topic with sourced facts and interpretation
- `mixed` — combine modes for broad changes

Status values:

- `PASS` — evidence supports the stated claim
- `FAIL` — evidence contradicts the claim or a check failed
- `INCOMPLETE` — some required evidence is missing
- `NOT SHOWN` — a claim was not demonstrated
- `NEEDS CAPTURE` — media/evidence tooling was unavailable or capture was deferred
- `EXPLANATORY` — understanding/documentation deck, not pass/fail verification
- `CONFLICTING` — sources disagree or evidence points in different directions
- `LOW_CONFIDENCE` — explanation is plausible but source coverage is weak

## Workflow

### 1. Classify intent

Identify:
- subject: what is being shown
- mode: verification, review, walkthrough, demo, docs, understanding, or mixed
- audience: reviewer, future maintainer, user, or self
- outcome: what the deck should let the human decide

If the user explicitly asked to generate/build/make the deck, proceed after this classification. If the request is ambiguous, propose the mode/outline and ask before generating.

### 2. Inspect sources

Gather only the context needed for the deck:
- git diff, commits, branch, and plans when verifying or reviewing changes
- relevant source files and tests
- docs or rendered output for docs decks
- URLs, screenshots, videos, logs, or command output supplied by the user
- architecture facts, diagrams, or command outputs needed for understanding decks

Distinguish sourced facts from interpretation. Do not invent rationale; if rationale is inferred, label it as inferred.

### 3. Choose output root

Default output root:

```text
${BEISLID_STATE_DIR:-~/.local/state/beislid}/show-me/<repo>/<timestamp>/
```

Repo-local output is allowed only when explicitly requested or configured:

```text
.beislid/show-me/<timestamp>/
```

Generated decks are local artifacts and should not be committed in v1. `.lavish/` supplemental wrappers are ignored local artifacts by default; commit generated decks or wrappers only for explicit docs/example workflow intent.

### 4. Gather evidence

Use available tools opportunistically:
- command logs for tests, builds, lint, docs generation, CLI demos, or inspections
- existing images/videos/GIFs supplied by the user
- screenshots or recordings when tools are available
- rendered docs pages when relevant
- diffs, file-role tables, and code excerpts for code walkthroughs
- diagrams when they clarify the subject

Ask before destructive, mutating, expensive, long-running, or externally visible actions.

If evidence is unavailable, add a visible `NOT SHOWN` or `NEEDS CAPTURE` block. Never imply missing evidence exists.

### 5. Create the artifact

For `understanding` decks with `EXPLANATORY` status, bias toward a visual decision deck by default:
- cards over long paragraphs
- side-by-side comparisons over dense tables
- flow diagrams for relationships, lifecycle, and data flow
- decision-tree framing for unresolved product choices
- “what gets saved” panels for backend/data behavior
- PM/reviewer checklist cards for open decisions

Create a local source/evidence directory. HTML rendering can use CDN presentation libraries (`marked`, DOMPurify, Mermaid, Highlight.js`) when available; source JSON, logs, and copied media remain local, and Markdown source is visible as a fallback if libraries fail to load.

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


The rendered `index.html` should be polished and human-reviewable:
- dark portfolio/report style unless the subject calls for another style
- sidebar, sticky nav, or clear table of contents when useful
- high-signal sections/chapters, not necessarily slide-only pages
- summary and status near the top
- cards, tables, callouts, media panels, and readable code/diff blocks
- command logs rendered in terminal-style panels
- provenance and caveats at the end

### 5b. Route optional Lavish inspection

After `index.html` exists, and only then, evaluate repo `beislid:visual_surfaces` for effective workflow `show-me`:
- absent config or `off`: keep the normal portable deck result and do not mention or invoke Lavish
- `suggest`: mention the rendered deck can be inspected in Lavish, without creating `.lavish/` output or invoking a command
- `prompt`: ask before opening in interactive runs; unattended runs keep the portable deck unless the run envelope/action policy already grants visual-surface invocation
- `auto`: invoke the configured provider with the rendered deck path only when action policy permits it

If a wrapper is needed for the prompt envelope, write it under `.lavish/show-me/` or the configured `artifact_root` equivalent and apply `artifact_retention` only to that supplemental wrapper. Disabled plugin state, missing command binaries or `npx`, declined prompts, command/editor failures, missing feedback, and freeform-only annotations are visible non-fatal fallbacks to the normal deck result. Never discard the canonical deck because Lavish was declined or unavailable.

### 6. Report results

Return:
- path to `index.html`
- path to `show-me.json`
- deck status/verdict
- evidence included
- evidence missing or marked `NEEDS CAPTURE`
- redactions or media-sensitivity warnings
- Lavish routing result when visual surfaces were active: effective mode, opened/suggested/fallback, supplemental wrapper path if any, and retention policy

Do not claim the subject passes unless fresh evidence in the deck supports that claim. Freeform Lavish annotations never change the deck status or verification claim unless the accepted change is copied into the canonical deck source/result.

## Portable document model

`show-me.json` should use this shape or a compatible superset:

```json
{
  "title": "string",
  "subtitle": "string",
  "mode": "verification|review|code-walkthrough|ui-demo|cli-demo|docs|understanding|mixed",
  "status": "PASS|FAIL|INCOMPLETE|NOT SHOWN|NEEDS CAPTURE|EXPLANATORY|CONFLICTING|LOW_CONFIDENCE",
  "presentation": "report|visual-deck|evidence-deck",
  "summary": "string",
  "sections": [
    {
      "title": "string",
      "purpose": "string",
      "blocks": []
    }
  ],
  "assets": [],
  "logs": [],
  "provenance": {}
}
```

Sections are chapters of a portfolio/report. They may look like slides when useful, but long-form sections are preferred for technical walkthroughs.

`presentation` is optional. Omit it to use the renderer defaults.

Presentation defaults:
- `understanding` + `EXPLANATORY` → `visual-deck`
- `verification`, `cli-demo`, `ui-demo` → `evidence-deck`
- `docs`, `review`, `code-walkthrough`, `mixed` → `report` unless explicitly set

Supported block types and canonical content keys:
- `markdown` — `markdown`
- `table` — `columns`, `rows`
- `code` — `code`, optional `language`
- `diff` — `diff`
- `diagram` — `diagram`, optional `language: "mermaid"` for Mermaid source; copied SVG assets still use media fields
- `command-log`
- `image`
- `video`
- `gif`
- `callout` — `text`, optional `title`/`tone`
- `verdict` — `status`, `text`
- `needs-capture`
- `file-role-table`

Pi tooling normalizes common aliases like `content`, `body`, and table `headers`, but generated source should prefer canonical keys.

## Evidence requirements

Command evidence must include:
- command
- cwd
- timestamp
- exit status
- relevant stdout/stderr in the deck or linked full log

Assets must include:
- original source path or capture method
- copied asset path
- type
- caption
- hash when practical
- media sensitivity warning if the content may contain private data

Understanding decks must include:
- source files/docs/commands inspected
- citations or file references for factual claims
- a clear split between facts, interpretation, and open questions

Failure decks are valid output. If a check fails, generate the deck with `FAIL` or `INCOMPLETE`, include the failure evidence, and add suggested next checks.

## Provenance

Record when available:
- timestamp
- cwd
- repo/root
- branch
- commit
- dirty status
- generator/version information
- skill version if known
- agent/model/session metadata if available
- concise task context and rationale notes
- command list and exit codes
- asset hashes
- redactions performed

Do not dump the full chat transcript by default. Include only the context and rationale needed to understand the deck.

## Redaction and privacy

Text logs, JSON, and rendered HTML should receive best-effort secret redaction. Note redactions in provenance.

Screenshots, videos, and GIFs may contain sensitive information. Warn about this unless a real redaction tool was used. Do not claim media is redacted unless it is.

## Pi tooling note

If Pi `show_me_*` tools or `/show-me` commands are available, use them to create, update, capture, and render the deck. When the deck-builder extension is also enabled, the portable skill wrapper is `/show-me-skill` and `/show-me` stays with deck management; use whichever command is actually bound in the current Pi install. Prefer `show_me_run_command` for command evidence so stdout/stderr, exit status, timestamps, cwd, logs, and redactions are captured consistently. Prefer `show_me_add_asset` for existing screenshots, videos, GIFs, and diagrams so files are copied into the deck with hashes, provenance, captions, and media sensitivity warnings. Use `show_me_capture_browser_screenshot` for browser screenshots when Playwright is already available; use `show_me_capture_screen_screenshot` for screen/window screenshots when the platform tool is present; use `show_me_record_terminal` for asciinema-backed terminal recordings; use `show_me_convert_video_to_gif` and `show_me_convert_gif_to_video` for local media conversion helpers. If any of those helpers cannot run, use `show_me_add_needs_capture` or the helper's generated `NEEDS_CAPTURE` block instead of pretending evidence exists. If the tools are not available, generate the files manually using the artifact contract above.

Future Pi tooling should accelerate this skill, not replace its behavior.
