#!/usr/bin/env python3
"""Static conformance tests for setup's just-in-time prompt routing."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "skills" / "setup"
ROUTER = SETUP / "SKILL.md"

TOP_LEVEL = {
    "update.md": ("# setup update v1", "✓ setup/update v1 loaded", 4_500),
    "first-run.md": ("# setup first run v1", "✓ setup/first-run v1 loaded", 13_000),
    "menu.md": ("# setup menu v1", "✓ setup/menu v1 loaded", 9_000),
    "write-and-report.md": ("# setup write and report v1", "✓ setup/write-and-report v1 loaded", 5_000),
    "agents-integration.md": ("# setup AGENTS integration v1", "✓ setup/agents-integration v1 loaded", 4_000),
    "parse-recovery.md": ("# setup parse recovery v1", "✓ setup/parse-recovery v1 loaded", 4_000),
}

SECTIONS = {
    "scopes-quality-gates": "Configure one gate model",
    "explore": "Configure kickoff explore skill?",
    "model-routing": "Configure the canonical `model_routing` block",
    "visual-surfaces": "Configure visual surfaces?",
    "workflow-signals": "Configure workflow signals?",
    "babysit": "Configure the canonical `beislid:babysit` block",
    "agent-isolation": "Configure the canonical `beislid:agent_isolation` block",
    "translation-sync": "Configure `translation_sync.skill`",
    "browser-compatibility": "Configure `browser_compat.skill`",
    "domain-capture": "Configure `domain_expert.agent` together",
    "pr-description-formatter": "Configure `pr_description.formatter_skill`",
    "guided-walkthrough": "Configure `guided_walkthrough.threshold_files`",
    "clean-evaluator": "Configure clean evaluator?",
    "fresh-eyes": "Configure final fresh-eyes behavior?",
    "ship-time-artifacts": "Configure ship-time planning-artifact narration?",
    "ticket-updates": "Configure ticket updates?",
    "planning-artifacts": "Configure user-approved planning artifacts?",
    "checkpoint-artifacts": "P0 executable checkpoint events",
    "lifecycle-actions": "Configure lifecycle CLI actions?",
    "lifecycle-hooks": "Configure custom phase-boundary hooks?",
    "pr-review": "Use GitHub CLI to read PR reviews",
    "review-feedback-profiles": "review comments already carry agent-ready instructions",
    "pr-host": "Configure `pr_host.*` only when the derived remote is wrong",
}


def prompt_files() -> list[Path]:
    return [ROUTER, *sorted(SETUP.glob("*.md")), *sorted((SETUP / "sections").glob("*.md"))]


class SetupSkillRoutingTests(unittest.TestCase):
    def test_router_is_small_and_routes_without_embedding_optional_interviews(self) -> None:
        text = ROUTER.read_text(encoding="utf-8")
        self.assertLessEqual(ROUTER.stat().st_size, 7_000)
        for name in TOP_LEVEL:
            self.assertIn(f"]({name})", text)
        self.assertIn("beislid resource resolve workflow-md-format", text)
        self.assertIn("beislid resource resolve probe-semantics", text)
        self.assertIn("exact sibling resource", text)
        self.assertNotIn("### Scopes & quality gates", text)
        self.assertNotIn("### Lifecycle actions", text)

    def test_top_level_auxiliaries_have_headings_stamps_and_budgets(self) -> None:
        for name, (heading, stamp, budget) in TOP_LEVEL.items():
            path = SETUP / name
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                text = path.read_text(encoding="utf-8")
                self.assertEqual(text.splitlines()[0], heading)
                self.assertIn(stamp, text)
                self.assertLessEqual(path.stat().st_size, budget)

    def test_every_optional_section_has_one_jit_owner_and_menu_route(self) -> None:
        menu = (SETUP / "menu.md").read_text(encoding="utf-8")
        corpus = prompt_files()
        actual_slugs = {path.stem for path in (SETUP / "sections").glob("*.md")}
        self.assertEqual(actual_slugs, set(SECTIONS), "setup section registry and files must match exactly")
        for slug, marker in SECTIONS.items():
            path = SETUP / "sections" / f"{slug}.md"
            with self.subTest(slug=slug):
                self.assertTrue(path.is_file())
                text = path.read_text(encoding="utf-8")
                self.assertEqual(text.splitlines()[0], f"# setup section {slug} v1")
                self.assertIn(f"✓ setup/section-{slug} v1 loaded", text)
                self.assertLessEqual(path.stat().st_size, 8_000)
                self.assertIn(f"](sections/{slug}.md)", menu)
                owners = [candidate for candidate in corpus if marker in candidate.read_text(encoding="utf-8")]
                self.assertEqual(owners, [path], f"marker {marker!r} must have one owner")

    def test_existing_local_resource_compatibility_files_remain(self) -> None:
        for name in ("workflow-md-format.md", "probe-semantics.md"):
            path = SETUP / name
            with self.subTest(name=name):
                self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
