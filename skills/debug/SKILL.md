---
name: debug
description: "Use when encountering any bug, test failure, or unexpected behavior. Requires root cause investigation before proposing fixes. No guessing."
---

# Debug Method

Find the root cause before touching code. No quick fixes, no guessing, no shotgun debugging.

<HARD-GATE>
Do NOT propose or implement a fix until you have identified the root cause with evidence. "It's probably X" is not a root cause.
</HARD-GATE>

## Phases

### 1. Reproduce
- Read the error message carefully — the full stack trace, not just the last line
- Reproduce the failure consistently
- If you can't reproduce it, you don't understand it yet

### 2. Investigate
- Check recent changes (`git log`, `git diff`) that could have introduced the issue
- Find a working reference — when did this last work? What's different?
- Trace the data flow from input to error point
- In multi-component systems, isolate which component fails first

### 3. Hypothesize
- Form a single hypothesis based on evidence gathered
- Test it minimally — the smallest change that proves or disproves the hypothesis
- If disproved, go back to step 2 with new information
- If you're stuck after 3 hypotheses, say "I don't understand this yet" and surface to the user

### 4. Fix
- Write a failing test that captures the bug
- Implement the fix — one change at a time
- Verify the test goes from red to green
- Run the full suite to check for regressions

## Red Flags

Stop yourself if you're thinking:
- "Let me just try changing X" — that's guessing
- "Quick fix for now" — that's deferring understanding
- "Multiple changes at once" — that's making it harder to know what worked
- "I don't fully understand but this should work" — go back to investigate
