---
name: verify
description: "Use before claiming work is complete, fixed, or passing. Requires running verification commands and reading output before making any success claims. Evidence before assertions."
---

# Check Done

## Project guidance preflight

If `.beislid/workflow.md` has `beislid:skill_guidance`, load `all` and `verify` guidance before proceeding; stop on missing/empty `must-read`; report loaded/missing.

No completion claims without fresh verification evidence. Period.

<HARD-GATE>
Before ANY claim that work is done, tests pass, a bug is fixed, or code is working — you MUST run the verification command, read the output, and confirm it matches the claim.
</HARD-GATE>

## The Gate

For every positive claim about work state:

1. **Identify** the verification command (test suite, linter, build, curl, etc.)
2. **Run it** fresh — not from memory, not from a previous run
3. **Read** the actual output
4. **Confirm** the output supports the claim
5. **Then** make the claim

## What Requires Evidence

| Claim | Required evidence |
|---|---|
| "Tests pass" | Test command output showing 0 failures |
| "Linter clean" | Linter output showing 0 errors |
| "Build succeeds" | Build command with exit code 0 |
| "Bug is fixed" | Failing test now passes (red to green) |
| "Feature works" | Test or manual verification output |

## Proof Requirements

When a Work Contract includes `proof_requirements`, match verification evidence to that vocabulary before claiming done. A command log can satisfy `command_gate`, review output can satisfy `review` or `fresh_eyes`, CI status can satisfy `ci_check`, and a deck/screenshot can satisfy `screenshot_show_me`. Missing required proof means stop and report the missing proof or human interrupt; do not downgrade it to advisory in chat.

## Red Flags

These words in your response without preceding evidence mean you're guessing:
- "should work", "probably works", "seems to be working"
- "I believe this fixes", "this should resolve"
- "tests should pass now"

Replace with: run the command, paste the output, state the fact.

## After Subagent Work

Agent success reports are not evidence. After a subagent completes:
1. Check the VCS diff
2. Run verification independently
3. Then confirm

## Visual Proof

If the user explicitly asks for a richer visual proof deck, invoke `show-me`. If verification would be clearer as screenshots, videos, diffs, command logs, or a browsable HTML report, suggest `show-me` and wait for a direct user request. Do not run `show-me` automatically; it is a manual/user-requested escalation in v1.
