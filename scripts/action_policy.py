#!/usr/bin/env python3
"""Deterministic Beislið action-risk policy evaluator.

The evaluator intentionally accepts explicit JSON input instead of attempting to
parse arbitrary shell commands. Orchestrators should pass an action id plus the
classes they know. A small registry and conservative heuristics fill in common
cases, but callers remain responsible for declaring action intent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

DECISIONS = ("allow", "ask", "deny")
DECISION_RANK = {"allow": 0, "ask": 1, "deny": 2}
RUN_MODES = ("supervised-auto", "unattended-auto")
ACTION_CLASSES = (
    "read",
    "workspace-write",
    "dependency-install",
    "network-read",
    "git-local",
    "git-remote",
    "destructive",
    "secret-bearing",
)
PROTECTED_CLASSES = ("destructive", "secret-bearing")
SANDBOX_BASELINES = ("none", "non-default-branch", "separate-worktree", "host-sandbox")
BASELINE_RANK = {name: idx for idx, name in enumerate(SANDBOX_BASELINES)}

# Assignment-shaped only (`KEY=...` / `key: ...`): bare substrings such as
# `tokenizer.py` must not infer secret-bearing. Compound segments around the
# keyword (`GITHUB_TOKEN=`, `db_password:`) still match; embedded fragments
# (`tokenizer`, `passwordless`, `monkey=`) do not.
SECRETISH_TEXT = re.compile(
    r"(?i)(authorization\s*:\s*bearer\b"
    r"|\b(?:[a-z0-9]+[_-])*(?:api[_-]?key|token|secret|password|private[_-]?key|auth[_-]?header)"
    r"(?:[_-][a-z0-9]+)*\b[\"']?\s*[:=]\s*\S)"
)
SECRETISH_ENV = re.compile(r"(?i)\$\{?(TOKEN|SECRET|PASSWORD|API[_-]?KEY|AUTH|GITHUB_TOKEN)\}?")

KNOWN_ACTIONS: dict[str, dict[str, Any]] = {
    "file.read": {"classes": ["read"], "description": "Read a workspace file"},
    "file.write": {"classes": ["workspace-write"], "description": "Create or modify a workspace file"},
    "git.status": {"classes": ["read"], "description": "Inspect git status"},
    "git.commit": {"classes": ["workspace-write", "git-local"], "description": "Create a local git commit"},
    "git.push": {"classes": ["git-remote"], "description": "Push commits to a remote"},
    "gh.issue.view": {"classes": ["network-read"], "description": "Read an issue through gh"},
    "ticket.update": {"classes": ["network-read", "git-remote"], "description": "Update a ticket body through tracker APIs"},
    "gh.pr.create": {"classes": ["git-remote"], "description": "Create a pull request"},
    "pr.review.reply": {"classes": ["git-remote"], "description": "Post a PR review reply"},
    "dependency.install": {"classes": ["workspace-write", "dependency-install", "network-read"], "description": "Install dependencies"},
    "shell.rm": {"classes": ["workspace-write", "destructive"], "description": "Delete files"},
}

DEFAULT_POLICY: dict[str, Any] = {
    "modes": {
        "supervised-auto": {
            "rules": {
                "read": "allow",
                "network-read": "allow",
                "workspace-write": "allow",
                "dependency-install": "ask",
                "git-local": "allow",
                "git-remote": "ask",
                "destructive": "deny",
                "secret-bearing": "ask",
            },
            "unknown_action": "allow",
            "unclassified_action": "allow",
            "sandbox": {"minimum": "none", "on_uncommitted_changes": "allow"},
        },
        "unattended-auto": {
            "rules": {
                "read": "allow",
                "network-read": "allow",
                "workspace-write": "ask",
                "dependency-install": "ask",
                "git-local": "ask",
                "git-remote": "deny",
                "destructive": "deny",
                "secret-bearing": "deny",
            },
            "unknown_action": "ask",
            "unclassified_action": "ask",
            "sandbox": {"minimum": "non-default-branch", "on_uncommitted_changes": "ask"},
        },
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise SystemExit("classes must be a string or list of strings")


def stricter(a: str, b: str) -> str:
    return a if DECISION_RANK[a] >= DECISION_RANK[b] else b


def validate_decision(value: str, field: str) -> str:
    if value not in DECISIONS:
        raise SystemExit(f"invalid decision for {field}: {value}")
    return value


def validate_baseline(value: str, field: str) -> str:
    if value not in SANDBOX_BASELINES:
        raise SystemExit(f"invalid sandbox baseline for {field}: {value}")
    return value


def normalize_policy(policy: dict[str, Any]) -> dict[str, Any]:
    merged = deep_merge(DEFAULT_POLICY, policy or {})
    modes = merged.get("modes")
    if not isinstance(modes, dict):
        raise SystemExit("policy.modes must be an object")
    for mode, mode_policy in modes.items():
        if mode not in RUN_MODES:
            raise SystemExit(f"invalid run mode in policy: {mode}")
        if not isinstance(mode_policy, dict):
            raise SystemExit(f"policy.modes.{mode} must be an object")
        rules = mode_policy.get("rules", {})
        if not isinstance(rules, dict):
            raise SystemExit(f"policy.modes.{mode}.rules must be an object")
        for cls, decision in rules.items():
            if cls not in ACTION_CLASSES:
                raise SystemExit(f"invalid action class in policy: {cls}")
            validate_decision(str(decision), f"{mode}.{cls}")
        for field in ("unknown_action", "unclassified_action"):
            validate_decision(str(mode_policy.get(field, "ask")), f"{mode}.{field}")
        actions = mode_policy.get("actions", {})
        if not isinstance(actions, dict):
            raise SystemExit(f"policy.modes.{mode}.actions must be an object")
        for action_id, decision in actions.items():
            validate_decision(str(decision), f"{mode}.actions.{action_id}")
        sandbox = mode_policy.get("sandbox", {})
        if not isinstance(sandbox, dict):
            raise SystemExit(f"policy.modes.{mode}.sandbox must be an object")
        validate_baseline(str(sandbox.get("minimum", "none")), f"{mode}.sandbox.minimum")
        validate_decision(str(sandbox.get("on_uncommitted_changes", "ask")), f"{mode}.sandbox.on_uncommitted_changes")
    return merged


def infer_secret_bearing(action: str, command: str, metadata: dict[str, Any]) -> bool:
    haystack = " ".join([action or "", command or "", json.dumps(metadata or {}, sort_keys=True)])
    return bool(SECRETISH_TEXT.search(haystack) or SECRETISH_ENV.search(haystack))


def sandbox_decision(mode_policy: dict[str, Any], sandbox_status: dict[str, Any], run_mode: str) -> tuple[str, list[dict[str, str]], list[str], str]:
    sandbox_policy = mode_policy.get("sandbox", {})
    required = str(sandbox_policy.get("minimum", "none"))
    actual = str(sandbox_status.get("baseline", "none"))
    validate_baseline(required, "sandbox.minimum")
    validate_baseline(actual, "sandbox_status.baseline")

    decision = "allow"
    matched: list[dict[str, str]] = []
    hints: list[str] = []

    if BASELINE_RANK[actual] < BASELINE_RANK[required]:
        decision = "ask"
        matched.append({"type": "sandbox", "rule": "minimum", "decision": "ask"})
        hints.append(f"Run {run_mode} from at least {required} isolation; current baseline is {actual}.")

    if sandbox_status.get("default_branch") is True and required != "none":
        decision = stricter(decision, "ask")
        matched.append({"type": "sandbox", "rule": "default_branch", "decision": "ask"})
        hints.append("Switch to a non-default branch before unattended side effects.")

    if sandbox_status.get("uncommitted_changes") is True:
        change_decision = str(sandbox_policy.get("on_uncommitted_changes", "ask"))
        decision = stricter(decision, validate_decision(change_decision, "sandbox.on_uncommitted_changes"))
        matched.append({"type": "sandbox", "rule": "uncommitted_changes", "decision": change_decision})
        hints.append("Review or isolate existing uncommitted changes before proceeding.")

    return decision, matched, hints, required


def policy_summary(policy: dict[str, Any]) -> dict[str, Any]:
    effective = normalize_policy(policy or {})
    modes: dict[str, Any] = {}
    for mode in RUN_MODES:
        mode_policy = effective["modes"][mode]
        modes[mode] = {
            "rules": mode_policy["rules"],
            "unknown_action": mode_policy.get("unknown_action", "ask"),
            "unclassified_action": mode_policy.get("unclassified_action", "ask"),
            "sandbox": mode_policy.get("sandbox", {}),
            "actions": mode_policy.get("actions", {}),
        }
    return {
        "status": "ok",
        "modes": modes,
        "classes": list(ACTION_CLASSES),
        "sandbox_baselines": list(SANDBOX_BASELINES),
        "known_actions": sorted(KNOWN_ACTIONS.keys()),
        "known_action_count": len(KNOWN_ACTIONS),
    }


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    run_mode = str(payload.get("mode") or payload.get("run_mode") or "supervised-auto")
    if run_mode not in RUN_MODES:
        raise SystemExit(f"invalid run mode: {run_mode}")

    policy = normalize_policy(payload.get("policy") or {})
    mode_policy = policy["modes"][run_mode]
    action = str(payload.get("action") or payload.get("action_id") or "")
    command = str(payload.get("command") or "")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

    registry_entry = KNOWN_ACTIONS.get(action, {})
    classes = set(as_list(registry_entry.get("classes")))
    explicit_classes = as_list(payload.get("classes"))
    classes.update(explicit_classes)
    if infer_secret_bearing(action, command, metadata):
        classes.add("secret-bearing")
    classes_list = sorted(classes, key=lambda item: ACTION_CLASSES.index(item) if item in ACTION_CLASSES else 999)

    decision = "allow"
    matched_rules: list[dict[str, str]] = []
    remediation: list[str] = []

    for cls in classes_list:
        if cls not in ACTION_CLASSES:
            raise SystemExit(f"invalid action class: {cls}")
        cls_decision = validate_decision(str(mode_policy["rules"].get(cls, "ask")), f"{run_mode}.{cls}")
        decision = stricter(decision, cls_decision)
        matched_rules.append({"type": "class", "class": cls, "decision": cls_decision})

    known = action in KNOWN_ACTIONS
    if not known:
        unknown_decision = validate_decision(str(mode_policy.get("unknown_action", "ask")), f"{run_mode}.unknown_action")
        decision = stricter(decision, unknown_decision)
        matched_rules.append({"type": "fallback", "rule": "unknown_action", "decision": unknown_decision})
    if not classes_list:
        unclassified_decision = validate_decision(str(mode_policy.get("unclassified_action", "ask")), f"{run_mode}.unclassified_action")
        decision = stricter(decision, unclassified_decision)
        matched_rules.append({"type": "fallback", "rule": "unclassified_action", "decision": unclassified_decision})

    # Per-action overrides replace class/fallback decisions, but are floored by
    # the protected classes: a deny earned through `destructive` or
    # `secret-bearing` (declared or inferred) can never be downgraded per
    # action. The only escape hatch is the explicit mode-wide class rule.
    action_overrides = mode_policy.get("actions", {})
    floor_clamped = False
    if action in action_overrides:
        action_decision = validate_decision(str(action_overrides[action]), f"{run_mode}.actions.{action}")
        protected_floor = "allow"
        for cls in PROTECTED_CLASSES:
            if cls in classes:
                protected_floor = stricter(protected_floor, str(mode_policy["rules"].get(cls, "ask")))
        applied_decision = stricter(action_decision, protected_floor)
        decision = applied_decision
        action_rule = {"type": "action", "action": action, "decision": action_decision}
        if applied_decision != action_decision:
            floor_clamped = True
            action_rule["applied"] = applied_decision
            action_rule["rule"] = "protected_class_floor"
            remediation.append(
                "Per-action overrides cannot downgrade destructive or secret-bearing decisions; "
                "if truly intended, set the mode-wide class rule explicitly instead."
            )
        matched_rules.append(action_rule)

    sandbox_status = payload.get("sandbox_status") if isinstance(payload.get("sandbox_status"), dict) else {}
    sandbox_dec, sandbox_rules, sandbox_hints, required_baseline = sandbox_decision(mode_policy, sandbox_status, run_mode)
    decision = stricter(decision, sandbox_dec)
    matched_rules.extend(sandbox_rules)
    remediation.extend(sandbox_hints)

    if decision == "ask":
        remediation.append("Ask for explicit human approval before running this action.")
    elif decision == "deny":
        remediation.append("Do not run this action in the current mode; change mode, policy, or action scope.")

    reason_parts = []
    if classes_list:
        reason_parts.append("classes=" + ",".join(classes_list))
    if not known:
        reason_parts.append("unknown action")
    if floor_clamped:
        reason_parts.append("action override capped by protected class floor")
    if sandbox_rules:
        reason_parts.append("sandbox baseline/status requires attention")
    if not reason_parts:
        reason_parts.append("default policy")

    return {
        "decision": decision,
        "mode": run_mode,
        "action": action or "(unspecified)",
        "known_action": known,
        "classes": classes_list,
        "matched_rules": matched_rules,
        "sandbox_status": {
            "baseline": str(sandbox_status.get("baseline", "none")),
            "required_baseline": required_baseline,
            "default_branch": bool(sandbox_status.get("default_branch", False)),
            "uncommitted_changes": bool(sandbox_status.get("uncommitted_changes", False)),
        },
        "requires_human": decision == "ask",
        "log_level": "info" if decision == "allow" else ("warning" if decision == "ask" else "error"),
        "reason": "; ".join(reason_parts),
        "remediation": remediation,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_json(args.input_file)
    if args.policy_file:
        payload["policy"] = load_json(args.policy_file)
    if args.mode:
        payload["mode"] = args.mode
    if args.action:
        payload["action"] = args.action
    if args.command_text:
        payload["command"] = args.command_text
    if args.classes:
        payload["classes"] = args.classes
    sandbox = dict(payload.get("sandbox_status") or {})
    if args.sandbox_baseline:
        sandbox["baseline"] = args.sandbox_baseline
    if args.default_branch:
        sandbox["default_branch"] = True
    if args.uncommitted_changes:
        sandbox["uncommitted_changes"] = True
    if sandbox:
        payload["sandbox_status"] = sandbox
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Beislið action-risk policy")
    subparsers = parser.add_subparsers(dest="subcommand")
    eval_parser = subparsers.add_parser("evaluate", help="evaluate an action policy envelope")
    eval_parser.add_argument("--input-file", help="JSON payload containing mode/action/classes/policy/sandbox_status")
    eval_parser.add_argument("--policy-file", help="JSON policy override file")
    eval_parser.add_argument("--mode", choices=RUN_MODES)
    eval_parser.add_argument("--action")
    eval_parser.add_argument("--class", dest="classes", action="append", choices=ACTION_CLASSES)
    eval_parser.add_argument("--command", dest="command_text", help="optional command text for conservative secret-bearing heuristics")
    eval_parser.add_argument("--sandbox-baseline", choices=SANDBOX_BASELINES)
    eval_parser.add_argument("--default-branch", action="store_true")
    eval_parser.add_argument("--uncommitted-changes", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="validate policy overrides and print the effective policy summary")
    validate_parser.add_argument("--policy-file", help="JSON policy override file")

    args = parser.parse_args(argv)
    if args.subcommand == "evaluate":
        envelope = evaluate(build_payload(args))
    elif args.subcommand == "validate":
        envelope = policy_summary(load_json(args.policy_file))
    else:
        parser.print_help(sys.stderr)
        return 2
    print(json.dumps(envelope, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
