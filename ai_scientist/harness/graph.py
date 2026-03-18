"""
Graph assembly — the single entry point for building the LangGraph graph.

Rules:
  - This is the ONLY file that calls StateGraph() and compiles the graph.
  - Node implementations live in agents/, reviewer/, etc.
  - Routing logic lives in conditional edge functions here or in circuit_breaker.py.
  - PostgresSaver is wired here; no other module creates checkpointers.

Usage:
    from ai_scientist.harness.graph import build_graph
    graph = build_graph(postgres_url="postgresql://...")
    result = await graph.ainvoke(initial_state("session-123"))
"""

from __future__ import annotations

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from ai_scientist.harness.circuit_breaker import circuit_breaker_node, route_after_breaker
from ai_scientist.harness.state import AIScientistState, ReviewStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Placeholder node stubs
# Replace each stub with the real import once the module is implemented.
# ---------------------------------------------------------------------------


async def _orientation_node(state: AIScientistState) -> dict:
    """Mandatory orientation: confirm cwd, read task list, git log. (stub)"""
    logger.info("[stub] orientation_node")
    return {}


async def _planner_node(state: AIScientistState) -> dict:
    """Output a ResearchProposal with quantitative success metric. (stub)"""
    logger.info("[stub] planner_node")
    return {}


async def _researcher_node(state: AIScientistState) -> dict:
    """Run ML experiment inside Docker container. (stub)"""
    logger.info("[stub] researcher_node")
    return {}


async def _reviewer_subgraph_node(state: AIScientistState) -> dict:
    """5-stage Reviewer pipeline. (stub)"""
    logger.info("[stub] reviewer_subgraph_node")
    return {}


async def _writer_node(state: AIScientistState) -> dict:
    """Generate LaTeX paper draft from experiment results. (stub)"""
    logger.info("[stub] writer_node")
    return {}


async def _evolution_node(state: AIScientistState) -> dict:
    """DSPy+GEPA prompt optimization (non-blocking). (stub)"""
    logger.info("[stub] evolution_node")
    return {}


async def _human_escalation_node(state: AIScientistState) -> dict:
    """Pause and notify human — circuit breaker or retry limit reached. (stub)"""
    logger.info("[stub] human_escalation_node — awaiting human intervention")
    return {}


async def _human_review_node(state: AIScientistState) -> dict:
    """PARTIAL_FAIL interrupt: wait for CLI approve/reject. (stub)"""
    logger.info("[stub] human_review_node — awaiting review decision")
    return {}


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------


def route_after_researcher(state: AIScientistState) -> str:
    """Route after experiment: retry, escalate, or review."""
    from ai_scientist.config.constants import MAX_EXPERIMENT_RETRIES

    if state["failure_count"] >= MAX_EXPERIMENT_RETRIES:
        return "escalate"
    if state["experiment_results"] is None:
        return "retry"
    return "review"


def route_after_reviewer(state: AIScientistState) -> str:
    """Route based on ValidationReport status."""
    report = state["validation_report"]
    if report is None:
        return "replan"

    if report.status == ReviewStatus.CRITICAL_FAIL:
        return "replan"
    if report.status == ReviewStatus.PARTIAL_FAIL:
        return "human_review"
    return "write"  # PASS


def route_after_human_review(state: AIScientistState) -> str:
    """Route after human reviews a PARTIAL_FAIL decision."""
    report = state["validation_report"]
    if report is None or report.human_note == "reject":
        return "replan"
    return "write"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------


def build_graph(postgres_url: str) -> StateGraph:
    """
    Assemble and compile the full AI Scientist LangGraph graph.

    Args:
        postgres_url: Connection string for PostgresSaver checkpointing.

    Returns:
        Compiled LangGraph graph ready for ainvoke() / astream().
    """
    builder = StateGraph(AIScientistState)

    # --- Nodes ---
    builder.add_node("orientation", _orientation_node)
    builder.add_node("circuit_breaker", circuit_breaker_node)
    builder.add_node("planner", _planner_node)
    builder.add_node("researcher", _researcher_node)
    builder.add_node("reviewer", _reviewer_subgraph_node)
    builder.add_node("writer", _writer_node)
    builder.add_node("evolution", _evolution_node)
    builder.add_node("human_escalation", _human_escalation_node)
    builder.add_node("human_review", _human_review_node)

    # --- Entry ---
    builder.add_edge(START, "orientation")
    builder.add_edge("orientation", "circuit_breaker")

    # --- Circuit breaker gate (fires before every meaningful transition) ---
    builder.add_conditional_edges(
        "circuit_breaker",
        route_after_breaker,
        {"escalate": "human_escalation", "continue": "planner"},
    )

    # --- Planner → human approval interrupt → researcher ---
    # Human approval is handled via LangGraph.interrupt() inside planner_node.
    builder.add_edge("planner", "researcher")

    # --- Researcher ---
    builder.add_conditional_edges(
        "researcher",
        route_after_researcher,
        {
            "retry": "researcher",       # retry same node
            "escalate": "human_escalation",
            "review": "reviewer",
        },
    )

    # --- Reviewer ---
    builder.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {
            "replan": "circuit_breaker",  # passes through breaker before replanning
            "human_review": "human_review",
            "write": "writer",
        },
    )

    # --- Human review (PARTIAL_FAIL) ---
    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "replan": "circuit_breaker",
            "write": "writer",
        },
    )

    # --- Writer → Evolution → END ---
    builder.add_edge("writer", "evolution")
    builder.add_edge("evolution", END)

    # --- Terminal nodes ---
    builder.add_edge("human_escalation", END)

    # --- Checkpointer ---
    # AsyncPostgresSaver is attached at runtime via graph.compile(checkpointer=...).
    # This factory returns the uncompiled builder so tests can compile without DB.
    return builder


async def compile_graph(postgres_url: str):  # type: ignore[return]
    """
    Compile the graph with a live PostgresSaver checkpointer.

    Separate from build_graph() so unit tests can compile without a DB connection.
    """
    async with await AsyncPostgresSaver.from_conn_string(postgres_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph(postgres_url).compile(checkpointer=checkpointer)
        return graph
