#!/usr/bin/env python3
"""Tests for the read-only workflow normalizer."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import workflow_normalizer  # noqa: E402


VALID_WORKFLOW = """<!-- beislid-workflow: v1 -->

# Test workflow

## Quality gates

```beislid:gates
- name: unit
  command: 'python3 -m unittest'
  parallel_safe: true
  mutates: false
```

## Gate sets

```beislid:gate_sets
sets:
  docs:
    gates:
      - name: docs-check
        command: 'python3 scripts/check_docs.py'
selectors:
  - name: docs
    paths: ['docs/**', '*.md']
    gate_sets: ['docs']
```

## Lifecycle actions

```beislid:lifecycle_actions
events:
  blueprint_approved:
    actions:
      - name: write-design
        type: artifact
        approval: auto
        path: 'plans/{feature}-design.md'
```

## Visual surfaces

```beislid:visual_surfaces
provider: lavish-axi
mode: prompt
artifact_retention: local
workflows:
  blueprint: suggest
```

## Model routing

```beislid:model_routing
defaults:
  models: ['anthropic:claude-sonnet-4.5']
  mode: prefer
overrides:
  - skills: ['blueprint']
    model: anthropic:claude-opus-4.8
    mode: require
```
"""


class WorkflowNormalizerTests(unittest.TestCase):
    def write_workflow(self, body: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name)
        workflow = repo / ".beislid" / "workflow.md"
        workflow.parent.mkdir()
        workflow.write_text(body, encoding="utf-8")
        return workflow

    def test_valid_config_normalizes_required_sections_and_source_hash(self) -> None:
        workflow = self.write_workflow(VALID_WORKFLOW)

        envelope = workflow_normalizer.normalize_workflow(workflow)

        expected_hash = hashlib.sha1(
            b"blob " + str(len(VALID_WORKFLOW.encode("utf-8"))).encode("ascii") + b"\0" + VALID_WORKFLOW.encode("utf-8")
        ).hexdigest()
        self.assertEqual(envelope["schema_version"], "beislid.workflow.normalizer.v1")
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["source"]["workflow_hash"], expected_hash)
        self.assertEqual(envelope["sections"]["gates"][0]["name"], "unit")
        self.assertEqual(envelope["sections"]["gate_sets"]["selectors"][0]["gate_sets"], ["docs"])
        self.assertEqual(
            envelope["sections"]["lifecycle_actions"]["events"]["blueprint_approved"]["actions"][0]["type"],
            "artifact",
        )
        self.assertEqual(envelope["sections"]["visual_surfaces"]["provider"], "lavish-axi")
        self.assertEqual(envelope["sections"]["model_routing"]["overrides"][0]["models"], ["anthropic:claude-opus-4.8"])
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual(envelope["errors"], [])

    def test_agent_isolation_is_absent_and_disabled_for_legacy_workflows(self) -> None:
        workflow = self.write_workflow(VALID_WORKFLOW)

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "ok")
        self.assertNotIn("agent_isolation", envelope["sections"])

    def test_agent_isolation_normalizes_explicit_opt_in_strategy(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:agent_isolation
orchestrator: native
delegate: manual
manual_root: repo-sibling
fallback:
  orchestrator: manual-transition-required
  delegate: sequential
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(
            envelope["sections"]["agent_isolation"],
            {
                "orchestrator": "native",
                "delegate": "manual",
                "manual_root": "repo-sibling",
                "fallback": {
                    "orchestrator": "manual-transition-required",
                    "delegate": "sequential",
                },
            },
        )

    def test_agent_isolation_rejects_unsafe_or_unknown_strategy_values(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:agent_isolation
orchestrator: automatic
delegate: shared
manual_root: relative/worktrees
fallback:
  orchestrator: sequential
  delegate: manual-transition-required
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(
            [error["path"] for error in envelope["errors"]],
            [
                "sections.agent_isolation.orchestrator",
                "sections.agent_isolation.delegate",
                "sections.agent_isolation.manual_root",
                "sections.agent_isolation.fallback.orchestrator",
                "sections.agent_isolation.fallback.delegate",
            ],
        )
        self.assertTrue(all(error["code"] == "invalid_value" for error in envelope["errors"]))

    def test_agent_isolation_normalizes_atomic_runtime_profile_contract(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:agent_isolation
orchestrator: current
delegate: manual
manual_root: /srv/beislid/worktrees
preparation:
  command: 'python3 scripts/prepare_workspace.py'
  readiness:
    - 'python3 scripts/check_workspace_ready.py'
runtime_profiles:
  integration:
    required_bindings:
      - PRIMARY_DATABASE_URL
      - SHADOW_DATABASE_URL
      - REDIS_URL
    provider:
      allocate: 'python3 scripts/runtime_provider.py allocate'
      verify: 'python3 scripts/runtime_provider.py verify'
      release: 'python3 scripts/runtime_provider.py release'
      reconcile: 'python3 scripts/runtime_provider.py reconcile'
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "ok")
        isolation = envelope["sections"]["agent_isolation"]
        self.assertEqual(isolation["fallback"]["delegate"], "sequential")
        self.assertEqual(isolation["preparation"]["command"], "python3 scripts/prepare_workspace.py")
        self.assertEqual(
            isolation["runtime_profiles"]["integration"]["required_bindings"],
            ["PRIMARY_DATABASE_URL", "SHADOW_DATABASE_URL", "REDIS_URL"],
        )
        self.assertEqual(
            isolation["runtime_profiles"]["integration"]["provider"]["reconcile"],
            "python3 scripts/runtime_provider.py reconcile",
        )

    def test_agent_isolation_rejects_ephemeral_root_and_invalid_runtime_profile(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:agent_isolation
orchestrator: manual
delegate: manual
manual_root: /tmp/beislid-worktrees
runtime_profiles:
  integration:
    required_bindings:
      - PRIMARY_DATABASE_URL
      - primary_database_url
      - PRIMARY_DATABASE_URL
    provider:
      allocate: ''
      verify: 42
      release: 'python3 provider.py release'
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(
            [(error["code"], error["path"]) for error in envelope["errors"]],
            [
                ("invalid_value", "sections.agent_isolation.manual_root"),
                ("invalid_value", "sections.agent_isolation.runtime_profiles.integration.required_bindings"),
                ("invalid_value", "sections.agent_isolation.runtime_profiles.integration.provider.allocate"),
                ("invalid_value", "sections.agent_isolation.runtime_profiles.integration.provider.verify"),
                ("missing_required_field", "sections.agent_isolation.runtime_profiles.integration.provider.reconcile"),
            ],
        )

    def test_agent_isolation_rejects_resolved_ephemeral_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            durable = root / "durable"
            ephemeral = root / "ephemeral"
            durable.mkdir()
            ephemeral.mkdir()
            link = durable / "linked"
            link.symlink_to(ephemeral, target_is_directory=True)

            for manual_root in (durable / ".." / "ephemeral" / "worktrees", link / "worktrees"):
                with self.subTest(manual_root=manual_root):
                    workflow = self.write_workflow(
                        f"""<!-- beislid-workflow: v1 -->

```beislid:agent_isolation
orchestrator: manual
delegate: sequential
manual_root: {manual_root}
```
"""
                    )
                    original_roots = workflow_normalizer.EPHEMERAL_MANUAL_ROOTS
                    self.addCleanup(setattr, workflow_normalizer, "EPHEMERAL_MANUAL_ROOTS", original_roots)
                    workflow_normalizer.EPHEMERAL_MANUAL_ROOTS = (ephemeral.resolve(),)

                    envelope = workflow_normalizer.normalize_workflow(workflow)

                    self.assertEqual(envelope["status"], "error")
                    self.assertIn(
                        ("invalid_value", "sections.agent_isolation.manual_root"),
                        [(error["code"], error["path"]) for error in envelope["errors"]],
                    )

    def test_agent_isolation_rejects_invalid_preparation_contract(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:agent_isolation
orchestrator: current
delegate: sequential
preparation:
  command: 42
  readiness: 'python3 scripts/check_ready.py'
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(
            [(error["code"], error["path"]) for error in envelope["errors"]],
            [
                ("invalid_value", "sections.agent_isolation.preparation.command"),
                ("invalid_value", "sections.agent_isolation.preparation.readiness"),
            ],
        )

    def test_d1_comments_and_inline_lists_follow_yaml_comment_rules(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: lint
  parallel_safe: true # optional
  autofix: npm run lint -- --fix # optional
  command: 'echo "a # b"'
  paths: [docs/**, *.md # optional]
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        gate = envelope["sections"]["gates"][0]
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(gate["parallel_safe"], True)
        self.assertEqual(gate["autofix"], "npm run lint -- --fix")
        self.assertEqual(gate["command"], 'echo "a # b"')
        self.assertEqual(gate["paths"], ["docs/**", "*.md"])
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual(envelope["errors"], [])

    def test_gate_exact_evidence_reuse_is_preserved(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: test
  command: python3 -m unittest
  mutates: false
  evidence_reuse:
    mode: exact
    environment:
      variables: [CI]
      commands:
        - [python3, --version]
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        reuse = envelope["sections"]["gates"][0]["evidence_reuse"]
        self.assertEqual("exact", reuse["mode"])
        self.assertEqual(["CI"], reuse["environment"]["variables"])
        self.assertEqual([["python3", "--version"]], reuse["environment"]["commands"])
        self.assertEqual([], envelope["warnings"])

    def test_invalid_gate_evidence_reuse_is_warned(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: test
  command: python3 -m unittest
  evidence_reuse:
    mode: maybe
    environment:
      variables: CI
      commands: [python3 --version]
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)
        paths = {warning["path"] for warning in envelope["warnings"]}
        self.assertIn("sections.gates[0].evidence_reuse.mode", paths)
        self.assertIn("sections.gates[0].evidence_reuse.environment.variables", paths)
        self.assertIn("sections.gates[0].evidence_reuse.environment.commands", paths)

    def test_d2_flow_maps_are_rejected_even_inside_registered_scopes(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:scopes
- name: frontend
  paths: ['apps/web/**']
  gates:
    - name: lint
      command: 'pnpm lint'
```

```beislid:gates
- { name: lint, command: 'pnpm lint' }
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "flow_map_unsupported")
        self.assertIn("block style", envelope["errors"][0]["message"])
        self.assertEqual(envelope["warnings"], [])

    def test_d3_parse_errors_report_absolute_workflow_line_numbers(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: ok
    command: bad-indent
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "malformed_block")
        self.assertIn("line 5", envelope["errors"][0]["message"])

    def test_d4_unknown_fence_keys_warn_with_absolute_lines(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:not_a_real_key
value: 1
```

```beislid:gates
- name: unit
  command: 'echo ok'
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "warning")
        self.assertEqual(envelope["warnings"][0]["code"], "unknown_fence_key")
        self.assertEqual(envelope["warnings"][0]["path"], "sections.not_a_real_key")
        self.assertIn("line 3", envelope["warnings"][0]["message"])
        self.assertEqual(envelope["errors"], [])

    def test_d5_tier_enums_and_tier_mode_are_validated(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:model_routing
defaults:
  model: anthropic:claude-sonnet-4.5
tier_mode: someday
tiers:
  tiny: [openai:gpt-4]
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        codes = [error["code"] for error in envelope["errors"]]
        paths = [error["path"] for error in envelope["errors"]]
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(codes, ["invalid_value", "invalid_value"])
        self.assertEqual(paths, ["sections.model_routing.tiers.tiny", "sections.model_routing.tier_mode"])

    def test_d6_model_and_models_are_mutually_exclusive(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:model_routing
defaults:
  model: anthropic:claude-sonnet-4.5
  models: ['anthropic:claude-sonnet-4.5']
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "invalid_value")
        self.assertEqual(envelope["errors"][0]["path"], "sections.model_routing.defaults")
        self.assertIn("mutually exclusive", envelope["errors"][0]["message"])

    def test_d7_decimal_floats_parse_as_numbers(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: numbers
  weight: 1.5
  whole: 2
  exponent: 1e3
  trailing: 1.
  leading: .5
  version: 1.5.2
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        gate = envelope["sections"]["gates"][0]
        self.assertEqual(envelope["status"], "ok")
        self.assertIsInstance(gate["weight"], float)
        self.assertEqual(gate["weight"], 1.5)
        self.assertIsInstance(gate["whole"], int)
        self.assertEqual(gate["whole"], 2)
        self.assertEqual(gate["exponent"], "1e3")
        self.assertEqual(gate["trailing"], "1.")
        self.assertEqual(gate["leading"], ".5")
        self.assertEqual(gate["version"], "1.5.2")

    def test_d8_nested_inline_lists_raise_explicit_error(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: paths
  paths: [[a, b], c]
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "nested_inline_list")
        self.assertIn("block style", envelope["errors"][0]["message"])

    def test_d9_quoted_scalars_handle_escapes_and_literals(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: "line1\\nline2"
  single: 'don''t'
  literal: 'a\\nb'
```

```beislid:model_routing
defaults:
  model: "bad\\q"
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        gate = envelope["sections"]["gates"][0]
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(gate["name"], "line1\nline2")
        self.assertEqual(gate["single"], "don't")
        self.assertEqual(gate["literal"], "a\\nb")
        self.assertEqual(envelope["errors"][0]["code"], "unknown_escape")

    def test_d9b_unterminated_quotes_error(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: "abc
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "unterminated_quote")
        self.assertIn("line 4", envelope["errors"][0]["message"])

    def test_duplicate_blocks_warn_and_first_occurrence_wins(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:gates
- name: first
  command: 'echo first'
```

```beislid:gates
- name: second
  command: 'echo second'
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "warning")
        self.assertEqual(envelope["sections"]["gates"][0]["name"], "first")
        self.assertEqual(envelope["warnings"][0]["code"], "duplicate_key")
        self.assertEqual(envelope["warnings"][0]["path"], "sections.gates")
        self.assertEqual(envelope["errors"], [])

    def test_invalid_version_stamp_is_error_and_cli_nonzero(self) -> None:
        workflow = self.write_workflow("# missing stamp\n")

        envelope = workflow_normalizer.normalize_workflow(workflow)
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "workflow_normalizer.py"), "--json", "--workflow", str(workflow)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "invalid_version_stamp")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["status"], "error")

    def test_beislid_cli_workflow_normalize_json_reads_current_repo_workflow(self) -> None:
        workflow = self.write_workflow(VALID_WORKFLOW)
        repo = workflow.parent.parent

        proc = subprocess.run(
            [str(ROOT / "bin" / "beislid"), "workflow", "normalize", "--json"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        envelope = json.loads(proc.stdout)
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["sections"]["gates"][0]["command"], "python3 -m unittest")


if __name__ == "__main__":
    unittest.main(verbosity=2)
