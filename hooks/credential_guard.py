#!/usr/bin/env python3
"""Standalone secrets filter for Claude Code PreToolUse hook.

Blocks Bash commands that would dump secrets to terminal output.
Stdlib-only. Ships with sensible defaults; override by placing a
credential_guard.json next to this file or pointing CREDENTIAL_GUARD_CONFIG
at a JSON path.
"""

import json
import os
import re
import sys


DEFAULT_CONFIG = {
    "blocked_commands": ["printenv", "env", "set", "declare"],
    "blocked_substrings": [
        ".env", "credentials.json", "credentials.yml",
        ".netrc", ".pgpass", ".my.cnf",
        "SECRET", "TOKEN", "PASSWORD", "PRIVATE_KEY",
        "API_KEY", "APIKEY", "AWS_SECRET", "AWS_SESSION",
    ],
    "blocked_patterns": [
        r"echo.*\$.*KEY", r"echo.*\$.*SECRET",
        r"echo.*\$.*TOKEN", r"echo.*\$.*PASSWORD",
        r"cat.*\.pem$", r"cat.*\.key$",
        r"cat.*id_rsa", r"cat.*id_ed25519",
    ],
    "blocked_pipes": ["env |", "printenv |", "export |", "set |", "declare -x |"],
    "allow_export_with_args": True,
    "allowed_markers": [],
}


class SecretsFilter:
    def __init__(self, cfg: dict):
        self._blocked_commands: list[str] = cfg.get("blocked_commands", [])
        self._blocked_substrings: list[str] = cfg.get("blocked_substrings", [])
        self._blocked_patterns: list[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in cfg.get("blocked_patterns", [])
        ]
        self._blocked_pipes: list[str] = cfg.get("blocked_pipes", [])
        self._allow_export_with_args: bool = cfg.get("allow_export_with_args", True)
        self._allowed_markers: list[str] = cfg.get("allowed_markers", [])

    def _extract_subshell_command(self, command: str) -> str | None:
        parts = command.strip().split()
        if len(parts) >= 3 and parts[0] in ("bash", "sh") and parts[1] == "-c":
            inner = " ".join(parts[2:])
            if (inner.startswith('"') and inner.endswith('"')) or \
               (inner.startswith("'") and inner.endswith("'")):
                inner = inner[1:-1]
            return inner
        return None

    def _strip_heredoc_body(self, command: str) -> str:
        # Prose inside heredocs and -m "..." messages (PR bodies, commit
        # messages) shouldn't trigger substring blockers like `TOKEN`.
        result = re.sub(
            r"<<-?\s*['\"]?(\w+)['\"]?\s*\n.*?\n\s*\1\s*\)?",
            "HEREDOC_STRIPPED",
            command,
            flags=re.DOTALL,
        )
        result = re.sub(r'-m\s+"[^"]*"', '-m "MSG_STRIPPED"', result)
        result = re.sub(r"-m\s+'[^']*'", "-m 'MSG_STRIPPED'", result)
        return result

    def check(self, command: str) -> tuple[bool, str]:
        stripped = command.strip()
        if not stripped:
            return True, ""

        # Early allowlist: if a command contains a known-safe marker (e.g. the
        # path to a trusted sync script), skip all other checks. Markers must
        # be specific enough that no unrelated command would contain them.
        for marker in self._allowed_markers:
            if marker and marker in stripped:
                return True, ""

        inner = self._extract_subshell_command(stripped)
        if inner:
            allowed, reason = self.check(inner)
            if not allowed:
                return allowed, reason

        for cmd in self._blocked_commands:
            if f"$({cmd}" in stripped or f"`{cmd}" in stripped:
                return False, f"Blocked: command substitution contains `{cmd}` which may expose secrets."

        first_token = stripped.split()[0]

        if first_token == "export" and self._allow_export_with_args:
            tokens = stripped.split()
            if len(tokens) > 1 and tokens[1] != "|":
                return True, ""
            if len(tokens) == 1:
                return False, "Blocked: bare `export` dumps all environment variables. Use `export VAR=value` to set a specific variable."

        if first_token in self._blocked_commands:
            return False, f"Blocked: `{first_token}` may expose secrets in terminal output. Use Read tool on specific config files instead."

        for pipe_prefix in self._blocked_pipes:
            if pipe_prefix in stripped:
                src_cmd = pipe_prefix.rstrip(" |").strip()
                return False, f"Blocked: `{src_cmd}` piped output may expose secrets. Filter specific variables instead."

        check_text = self._strip_heredoc_body(stripped)
        check_lower = check_text.lower()

        for substr in self._blocked_substrings:
            if substr.lower() in check_lower:
                return False, f"Blocked: command contains `{substr}` which may reference secrets. Use Read tool to inspect files without terminal output."

        for pattern in self._blocked_patterns:
            if pattern.search(check_text):
                return False, f"Blocked: command matches secret pattern `{pattern.pattern}`. Avoid printing secrets to terminal."

        return True, ""


def _load_config() -> dict:
    override = os.environ.get("CREDENTIAL_GUARD_CONFIG")
    sibling = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "credential_guard.json",
    )
    for path in (override, sibling):
        if path and os.path.isfile(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
    return DEFAULT_CONFIG


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    sf = SecretsFilter(_load_config())
    allowed, reason = True, ""

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        allowed, reason = sf.check(command)

    if not allowed:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
        print(json.dumps(result))
