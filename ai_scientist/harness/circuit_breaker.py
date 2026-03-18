"""
[IMMUTABLE] Circuit breaker for the LangGraph Pregel super-step limit.

DO NOT modify this file without explicit user approval.
The hard limit MAX_PREGEL_SUPER_STEPS = 15 is a safety guardrail
defined in KB-07 and must not be raised by self-evolution.

Usage:
    graph.add_node("circuit_breaker", circuit_breaker_node)
    graph.add_conditional_edges("circuit_breaker", route_after_breaker, {...})
"""

import logging

from ai_scientist.config.constants import MAX_PREGEL_SUPER_STEPS
from ai_scientist.harness.state import AIScientistState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


def circuit_breaker_node(state: AIScientistState) -> dict:
    """
    Increment the super-step counter and check against the hard limit.

    Returns a state patch. The conditional edge `route_after_breaker`
    decides whether to continue or escalate to human intervention.
    """
    new_count = state["pregel_step_count"] + 1

    if new_count >= MAX_PREGEL_SUPER_STEPS:
        logger.warning(
            "Circuit breaker fired: pregel_step_count=%d >= MAX=%d. "
            "Escalating to human intervention.",
            new_count,
            MAX_PREGEL_SUPER_STEPS,
        )

    return {"pregel_step_count": new_count}


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------


def route_after_breaker(state: AIScientistState) -> str:
    """
    Called as a conditional edge after circuit_breaker_node.

    Returns:
        "escalate"  — step limit reached, hand off to human
        "continue"  — within limit, proceed normally
    """
    if state["pregel_step_count"] >= MAX_PREGEL_SUPER_STEPS:
        return "escalate"
    return "continue"
