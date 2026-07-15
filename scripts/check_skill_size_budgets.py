#!/usr/bin/env python3
"""Enforce hard size budgets for prompt-heavy skill files.

Phase 4 of the v0.2 migration keeps ready-for-review lightweight by splitting phase
protocols into JIT-loaded auxiliary files. This script enforces only hard caps;
soft targets live in the planning docs.
"""

from __future__ import annotations

import pathlib
import sys


# Hard caps are byte counts, not token estimates. Byte counts are deterministic
# across platforms and good enough to prevent context bloat regressions.
BUDGETS = {
    # ready-for-review/SKILL.md, phase-1-detect.md, and phase-4-submit.md were
    # bumped by 300 bytes each (BEI-137) to fit the crust-seam-protocol.md
    # delegation pointers (run-ledger init/finalize, gate selection) required
    # by the crust seam design; they were at ~100% of their prior caps.
    "skills/ready-for-review/SKILL.md": 10_300,
    "skills/ready-for-review/phase-1-detect.md": 5_300,
    "skills/ready-for-review/phase-2-gates.md": 7_000,
    "skills/ready-for-review/phase-3-review.md": 5_000,
    "skills/ready-for-review/phase-4-submit.md": 7_300,
    "skills/babysit/SKILL.md": 8_000,
    "skills/envelope/SKILL.md": 7_000,
    "skills/envelope/step-1-intake.md": 4_000,
    "skills/envelope/step-2-author.md": 4_000,
    "skills/envelope/step-3-approve.md": 4_000,
    "skills/envelope/step-4-export.md": 4_000,
    "skills/envelope/step-5-revise.md": 4_000,
    "skills/envelope/afk-rubric.md": 4_000,
    # kickoff/SKILL.md bumped by 400 bytes (BEI-137) for the crust-seam
    # run-ledger delegation pointer; it was at ~100% of its prior cap.
    "skills/kickoff/SKILL.md": 7_400,
    "skills/kickoff/step-1-ticket.md": 4_000,
    "skills/kickoff/step-2-context.md": 4_000,
    "skills/kickoff/step-3-team-guidance.md": 4_000,
    "skills/kickoff/step-4-readiness.md": 4_000,
    "skills/kickoff/step-4-checkpoint.md": 4_000,
    "skills/kickoff/step-5-scope.md": 4_000,
    "skills/kickoff/step-6-blueprint.md": 4_000,
    "skills/kickoff/step-7-discoveries.md": 4_000,
    "skills/kickoff/step-8-ticket-update.md": 4_000,
    "skills/implement/workspace-placement-protocol.md": 4_000,
    "skills/implement/workspace-placement-codex.md": 3_000,
    "skills/implement/workspace-placement-claude.md": 3_000,
    "skills/implement/workspace-placement-pi.md": 3_000,
    "skills/implement/workspace-placement-generic.md": 2_000,
    "skills/review-response/SKILL.md": 7_000,
    "skills/review-response/phase-1-detect.md": 6_000,
    "skills/review-response/phase-2-fix.md": 5_000,
    # phase-3-push.md bumped by 300 bytes (BEI-137) for the crust-seam gate
    # selection delegation pointer; it was at ~100% of its prior cap.
    "skills/review-response/phase-3-push.md": 5_300,
    "skills/walk-the-diff/SKILL.md": 6_000,
    "skills/walk-the-diff/phase-1-context.md": 4_000,
    "skills/walk-the-diff/phase-2-tour-plan.md": 4_000,
    "skills/walk-the-diff/phase-3-present.md": 4_000,
    "skills/walk-the-diff/phase-4-wrap.md": 4_000,
}

PHASE_AUX_HEADINGS = {
    "skills/ready-for-review/phase-1-detect.md": "# ready-for-review phase 1 detect v1",
    "skills/ready-for-review/phase-2-gates.md": "# ready-for-review phase 2 gates v1",
    "skills/ready-for-review/phase-3-review.md": "# ready-for-review phase 3 review v1",
    "skills/ready-for-review/phase-4-submit.md": "# ready-for-review phase 4 submit v1",
    "skills/envelope/step-1-intake.md": "# envelope step 1 intake v1",
    "skills/envelope/step-2-author.md": "# envelope step 2 author v1",
    "skills/envelope/step-3-approve.md": "# envelope step 3 approve v1",
    "skills/envelope/step-4-export.md": "# envelope step 4 export v1",
    "skills/envelope/step-5-revise.md": "# envelope step 5 revise v1",
    "skills/envelope/afk-rubric.md": "# afk-rubric v1",
    "skills/kickoff/step-1-ticket.md": "# kickoff step 1 ticket v1",
    "skills/kickoff/step-2-context.md": "# kickoff step 2 context v1",
    "skills/kickoff/step-3-team-guidance.md": "# kickoff step 3 team guidance v1",
    "skills/kickoff/step-4-readiness.md": "# kickoff step 4 readiness v1",
    "skills/kickoff/step-4-checkpoint.md": "# kickoff step 4 checkpoint v1",
    "skills/kickoff/step-5-scope.md": "# kickoff step 5 scope v1",
    "skills/kickoff/step-6-blueprint.md": "# kickoff step 6 blueprint v1",
    "skills/kickoff/step-7-discoveries.md": "# kickoff step 7 discoveries v1",
    "skills/kickoff/step-8-ticket-update.md": "# kickoff step 8 ticket update v1",
    "skills/implement/workspace-placement-protocol.md": "# workspace placement protocol v1",
    "skills/implement/workspace-placement-codex.md": "# workspace placement Codex adapter v1",
    "skills/implement/workspace-placement-claude.md": "# workspace placement Claude adapter v1",
    "skills/implement/workspace-placement-pi.md": "# workspace placement Pi adapter v1",
    "skills/implement/workspace-placement-generic.md": "# workspace placement generic adapter v1",
    "skills/review-response/phase-1-detect.md": "# review-response phase 1 detect v1",
    "skills/review-response/phase-2-fix.md": "# review-response phase 2 fix v1",
    "skills/review-response/phase-3-push.md": "# review-response phase 3 push v1",
    "skills/walk-the-diff/phase-1-context.md": "# walk-the-diff phase 1 context v1",
    "skills/walk-the-diff/phase-2-tour-plan.md": "# walk-the-diff phase 2 tour plan v1",
    "skills/walk-the-diff/phase-3-present.md": "# walk-the-diff phase 3 present v1",
    "skills/walk-the-diff/phase-4-wrap.md": "# walk-the-diff phase 4 wrap v1",
}

PHASE_AUX_FILES = set(PHASE_AUX_HEADINGS)


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    errors: list[str] = []

    for rel, max_bytes in BUDGETS.items():
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: missing required file")
            continue
        if rel in PHASE_AUX_FILES and path.is_symlink():
            errors.append(f"{rel}: must be a regular file, not a symlink")
            continue
        if not path.is_file():
            errors.append(f"{rel}: expected regular file")
            continue

        if rel in PHASE_AUX_HEADINGS:
            first_line = path.read_text(encoding="utf-8").splitlines()[0] if path.stat().st_size else ""
            expected = PHASE_AUX_HEADINGS[rel]
            if first_line != expected:
                errors.append(f"{rel}: first heading must be `{expected}`, got `{first_line}`")

        size = path.stat().st_size
        if size > max_bytes:
            errors.append(f"{rel}: {size} bytes exceeds hard cap {max_bytes}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    checked = ", ".join(f"{rel}≤{max_bytes}" for rel, max_bytes in BUDGETS.items())
    print(f"ok: skill size budgets satisfied ({checked})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
