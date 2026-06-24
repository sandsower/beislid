#!/usr/bin/env python3
"""Tests for the Beislið typed visual feedback helper.

Coverage labels for consistency checks: unknown action, malformed payload,
freeform-only feedback.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import visual_feedback  # noqa: E402


class VisualFeedbackTests(unittest.TestCase):
    def normalize(self, payload: str) -> dict[str, object]:
        return visual_feedback.normalize_visual_feedback(
            payload,
            expected_workflow="spec",
            expected_action="approve_or_revise_spec",
        )

    def test_accepts_json_approve_payload(self) -> None:
        result = self.normalize(
            '{"schema":"BEISLID_VISUAL_FEEDBACK_V1","workflow":"spec",'
            '"action":"approve_or_revise_spec","decision":"approve",'
            '"approval_note":"Looks ready"}'
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["decision"], "approve")
        self.assertEqual(result["action"], "approve_or_revise_spec")
        self.assertTrue(result["canonical_update_required"])

    def test_accepts_single_fenced_payload_when_prose_repeats_schema_name(self) -> None:
        result = self.normalize(
            """
            Here is the BEISLID_VISUAL_FEEDBACK_V1 response:

            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            approval_note: Looks ready
            ```
            """
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["decision"], "approve")

    def test_accepts_note_containing_schema_name_inside_single_payload(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            approval_note: BEISLID_VISUAL_FEEDBACK_V1 shape reviewed
            """
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["decision"], "approve")

    def test_normalizes_yaml_request_changes_to_revise(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: request_changes
            revision_summary: Tighten acceptance criteria
            must_change:
              - Add a fallback section
            nice_to_have: [Add examples]
            """
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["decision"], "revise")
        self.assertEqual(result["original_decision"], "request_changes")
        self.assertEqual(result["must_change"], ["Add a fallback section"])
        self.assertEqual(result["nice_to_have"], ["Add examples"])

    def test_preserves_hash_inside_quoted_yaml_scalars(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            approval_note: "Keep #audit-trail in the canonical note"
            must_change:
              - "Preserve #anchor references"
            nice_to_have: ['Keep #nice-to-have tags']
            """
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["approval_note"], "Keep #audit-trail in the canonical note")
        self.assertEqual(result["must_change"], ["Preserve #anchor references"])
        self.assertEqual(result["nice_to_have"], ["Keep #nice-to-have tags"])

    def test_strips_unquoted_yaml_comments(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            approval_note: Looks ready # sidebar note
            """
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["approval_note"], "Looks ready")

    def test_unknown_action_falls_to_manual_review(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: launch_downstream_workflow
            decision: approve
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "unknown_action")
        self.assertIsNone(result["decision"])
        self.assertTrue(result["canonical_update_required"])

    def test_malformed_payload_falls_to_manual_review(self) -> None:
        result = self.normalize("schema: BEISLID_VISUAL_FEEDBACK_V1\nworkflow: spec\n")

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "missing_required_field")
        self.assertIsNone(result["decision"])

    def test_freeform_only_feedback_is_not_a_gate_decision(self) -> None:
        result = self.normalize("I left some notes in the right sidebar; this is close.")

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "missing_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_rejects_nested_malformed_yaml_payload(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            metadata:
              workflow: spec
              action: approve_or_revise_spec
              decision: approve
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "malformed_payload")
        self.assertIsNone(result["decision"])

    def test_multiple_typed_payloads_are_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: revise
            must_change: [Tighten fallback docs]
            ```
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_duplicate_typed_payloads_are_ambiguous_even_when_identical(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_valid_plus_malformed_typed_payload_is_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            metadata:
              workflow: spec
              action: approve_or_revise_spec
              decision: approve
            ```
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_valid_fenced_plus_unfenced_malformed_typed_payload_is_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            schema: BEISLID_VISUAL_FEEDBACK_V1
            metadata:
              workflow: spec
              action: approve_or_revise_spec
              decision: approve
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_multiple_unfenced_typed_payloads_are_ambiguous(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve

            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: revise
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_schema_payload_plus_legacy_payload_is_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            ```yaml
            workflow: spec
            action: review_spec
            decision: revise
            ```
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_unknown_schema_payload_falls_to_manual_review(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V2
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "unknown_schema")
        self.assertIsNone(result["decision"])

    def test_schema_payload_plus_unknown_schema_payload_is_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V2
            workflow: spec
            action: launch_downstream_workflow
            decision: approve
            ```
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_schema_payload_plus_unfenced_unknown_schema_payload_is_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            schema: BEISLID_VISUAL_FEEDBACK_V2
            workflow: spec
            action: launch_downstream_workflow
            decision: approve
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_schema_payload_plus_legacy_unknown_action_is_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            ```yaml
            workflow: spec
            action: launch_downstream_workflow
            decision: approve
            ```
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_fenced_schema_payload_plus_unfenced_legacy_payload_is_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            workflow: spec
            action: review_spec
            decision: revise
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_fenced_schema_payload_plus_unfenced_legacy_unknown_action_is_ambiguous(self) -> None:
        result = self.normalize(
            """
            ```yaml
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            ```

            workflow: spec
            action: launch_downstream_workflow
            decision: approve
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "ambiguous_typed_feedback")
        self.assertIsNone(result["decision"])

    def test_duplicate_yaml_fields_are_malformed(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: approve_or_revise_spec
            decision: revise
            decision: approve
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "malformed_payload")
        self.assertIsNone(result["decision"])

    def test_duplicate_json_fields_are_malformed(self) -> None:
        result = self.normalize(
            '{"schema":"BEISLID_VISUAL_FEEDBACK_V1","workflow":"spec",'
            '"action":"approve_or_revise_spec","decision":"revise",'
            '"decision":"approve"}'
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "malformed_payload")
        self.assertIsNone(result["decision"])

    def test_explicit_empty_yaml_schema_is_malformed_not_legacy(self) -> None:
        result = self.normalize(
            """
            schema:
            workflow: spec
            action: approve_or_revise_spec
            decision: approve
            """
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "malformed_payload")
        self.assertIsNone(result["decision"])

    def test_explicit_empty_json_schema_is_malformed_not_legacy(self) -> None:
        result = self.normalize(
            '{"schema":"","workflow":"spec",'
            '"action":"approve_or_revise_spec","decision":"approve"}'
        )

        self.assertEqual(result["status"], "manual_review")
        self.assertEqual(result["reason"], "malformed_payload")
        self.assertIsNone(result["decision"])

    def test_legacy_phase_one_payload_without_schema_is_backward_compatible(self) -> None:
        result = self.normalize(
            """
            workflow: spec
            action: review_spec
            decision: approve
            """
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["decision"], "approve")
        self.assertEqual(result["action"], "approve_or_revise_spec")
        self.assertTrue(result["legacy_schema_omitted"])

    def test_legacy_phase_one_request_changes_without_schema_is_backward_compatible(self) -> None:
        result = self.normalize(
            """
            workflow: spec
            action: approve_or_revise_spec
            decision: request_changes
            must_change: [Clarify fallback]
            """
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["decision"], "revise")
        self.assertEqual(result["must_change"], ["Clarify fallback"])
        self.assertTrue(result["legacy_schema_omitted"])

    def test_phase_one_review_spec_action_is_backward_compatible(self) -> None:
        result = self.normalize(
            """
            schema: BEISLID_VISUAL_FEEDBACK_V1
            workflow: spec
            action: review_spec
            decision: approve
            """
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["action"], "approve_or_revise_spec")
        self.assertEqual(result["original_action"], "review_spec")


if __name__ == "__main__":
    unittest.main()
