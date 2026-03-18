"""
[IMMUTABLE] Claude Agent SDK hooks: deterministic firewall layer.

DO NOT modify this file without explicit user approval.
Hooks are the last line of defence before any tool call executes.
Self-evolution must not bypass or weaken these checks.

Hook types used (KB-09, KB-05):
  PreToolUse  — validate + optionally block a tool call before execution
  PostToolUse — inspect result, log, update metrics
  SessionStart — mandatory orientation routine

These hooks are registered via .claude/settings.json (Claude Agent SDK),
not called directly by Python code. This module defines the logic
that the hook shell commands delegate to.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blocked tool patterns (deterministic firewall)
# Extend this list to add new restrictions; never remove existing entries.
# ---------------------------------------------------------------------------

#: Tool calls whose name matches any of these prefixes are always blocked.
BLOCKED_TOOL_PREFIXES: tuple[str, ...] = (
    "bash__rm",           # prevent accidental file deletion
    "bash__sudo",         # no privilege escalation
    "bash__curl",         # network calls must go through tools/
    "bash__wget",
    "bash__pip",          # package management only via uv
    "bash__git_push",     # git push requires explicit user approval
)

#: Files that no tool call may write to (enforced in pre_tool_use).
IMMUTABLE_FILE_PATHS: tuple[str, ...] = (
    "ai_scientist/harness/circuit_breaker.py",
    "ai_scientist/harness/hooks.py",
    "ai_scientist/reviewer/statistical.py",
    "ai_scientist/config/constants.py",
    "ai_scientist/monitoring/health.py",
    "CLAUDE.md",
)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


def pre_tool_use(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a tool call before execution.

    Args:
        tool_name:  Name of the Claude tool being called.
        tool_input: Raw input dict from Claude.

    Returns:
        {"allow": True}  — permit execution
        {"allow": False, "reason": str}  — block execution

    This function is called by the PreToolUse hook shell command.
    """
    # --- Blocked tool prefix check ---
    for prefix in BLOCKED_TOOL_PREFIXES:
        if tool_name.startswith(prefix):
            reason = f"Tool '{tool_name}' is blocked by harness firewall (prefix: {prefix})."
            logger.warning("BLOCKED tool call: %s | reason: %s", tool_name, reason)
            return {"allow": False, "reason": reason}

    # --- Immutable file write check ---
    if tool_name in ("write_file", "edit_file", "str_replace_editor"):
        file_path: str = tool_input.get("path", tool_input.get("file_path", ""))
        for immutable in IMMUTABLE_FILE_PATHS:
            if immutable in file_path:
                reason = (
                    f"Write to IMMUTABLE file blocked: '{file_path}'. "
                    "Requires explicit user approval."
                )
                logger.warning("BLOCKED immutable write: %s", file_path)
                return {"allow": False, "reason": reason}

    return {"allow": True}


def post_tool_use(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_result: Any,
) -> None:
    """
    Inspect and log tool results after execution.

    Called by the PostToolUse hook shell command.
    Does not block; use pre_tool_use for blocking logic.
    """
    logger.debug(
        "Tool completed: name=%s | input_keys=%s",
        tool_name,
        list(tool_input.keys()),
    )


def session_start(session_id: str) -> list[str]:
    """
    Return the mandatory orientation steps for a new session.

    The Initializer Agent must execute these in order before any task work.
    Called by the SessionStart hook.

    Returns:
        Ordered list of shell commands to run.
    """
    return [
        "pwd",
        "git log --oneline -5",
        "cat tasks.json 2>/dev/null || echo 'No tasks.json found'",
        "cat TODO.md 2>/dev/null || echo 'No TODO.md found'",
    ]
