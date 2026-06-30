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

## PR reviews

```beislid:review_feedback_profiles
- name: coderabbit
  match:
    author_regex: 'coderabbitai'
  extract:
    prompt_regex: '```agent-prompt\\n(?P<prompt>.*?)```'
    prompt_format: markdown
```

## Ready-for-review

```beislid:clean_eval
mode: require
surface: auto
artifact_root: .beislid/clean-eval
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
        self.assertEqual(envelope["sections"]["clean_eval"]["mode"], "require")
        self.assertEqual(envelope["sections"]["visual_surfaces"]["provider"], "lavish-axi")
        self.assertEqual(envelope["sections"]["model_routing"]["overrides"][0]["models"], ["anthropic:claude-opus-4.8"])
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual(envelope["errors"], [])

    def test_warning_config_exits_successfully_with_warning_status(self) -> None:
        workflow = self.write_workflow(
            """<!-- beislid-workflow: v1 -->

```beislid:model_routing
defaults:
  model: anthropic:claude-sonnet-4.5
  when:
    branch: main
```
"""
        )

        envelope = workflow_normalizer.normalize_workflow(workflow)

        self.assertEqual(envelope["status"], "warning")
        self.assertEqual(envelope["warnings"][0]["code"], "reserved_field")
        self.assertEqual(envelope["errors"], [])

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

    def test_malformed_block_is_error(self) -> None:
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
