# roundup step 2 analyze v1

Authoritative JIT protocol for roundup Step 2. Load after a confirmed roster.

## Purpose

Produce one analysis card per ticket. Judgments here feed the pens in Step 3; no pen decisions are made yet, and no tickets are edited.

## Protocol

Print the Step 2 entry one-liner from `roundup-templates.md`.

For each rostered ticket, build a card with:

### AFK bar (contract-grade body)

A ticket meets the bar only when its **body alone** is an executable contract:

- **Clear acceptance criteria** — observable outcomes, not aspirations.
- **A Validation/Test Plan-style section** the runner can execute verbatim (runners treat it as non-negotiable acceptance input).
- **No unresolved human decisions** — open questions, "TBD", or competing options in the body fail the bar.

Apply envelope's evidence rule (afk-rubric-v0 judgment style): a claim that cannot be verified this session — a named command that doesn't exist, a path never explored, a dependency of unknown state — pushes the ticket below the bar. Record the **exact gaps** ("no Validation/Test Plan"; "AC ambiguous: does X include Y?"), specific enough to brief a `/spec` session.

### Human-shaped test

Independent of body quality: work needing design taste, user-facing judgment calls, or review conversation is HITL-shaped. Record why.

### Touch areas (text→tree)

Predict the directories/modules/globs the ticket will touch — and **explore before claiming**: ground every predicted area against the actual repo tree (`ls`, targeted `grep`); never scope from filenames or ticket prose alone. Record explored, dir-level areas.

### Dependency edges

- Tracker relations (blocks/blocked-by) are authoritative.
- Content-implied ordering ("builds on", shared contract files) is recorded with an explicit `inferred:` marker and a one-line reason.
- Dependencies on open tickets **outside** the roster are recorded as external blockers.

### Conflict flags

Pairwise-intersect touch areas across the roster. Overlapping areas get an advisory flag naming the shared area. Flags inform Step 3 wave assignment and the human's verdict; they decide nothing by themselves.

## Exit

Print the Step 2 exit one-liner. Required outputs: one card per ticket — AFK-bar verdict with exact gaps, human-shaped notes, explored touch areas, dependency edges (authoritative vs inferred), conflict flags.

## Tripwires

- No touch-area claim without in-session exploration.
- Gaps must be enrichment-brief quality: a `/spec` session could start from them directly.
- Inferred edges are never silently promoted to authoritative.
- Analysis reads the repo and tickets; it never writes either.
