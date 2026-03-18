"""
LangGraph State schema (Blackboard TypedDict).

Rules:
  - This is the ONLY place where AIScientistState is defined.
  - Nodes must NOT mutate state directly; use reducer functions below.
  - All fields are Optional where the pipeline has not yet produced a value.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ReviewStatus(str, Enum):
    PASS = "PASS"
    PARTIAL_FAIL = "PARTIAL_FAIL"
    CRITICAL_FAIL = "CRITICAL_FAIL"


class ReviewerStage(int, Enum):
    NOT_STARTED = 0
    STATISTICAL_VALIDATION = 1
    MVVC_FILTER = 2
    DEEP_REVIEWER_EVAL = 3
    S2AG_IMPACT_CHECK = 4
    EMPIRICAL_SUPREMACY = 5
    COMPLETE = 6


class FailureTier(str, Enum):
    """L1–L4 failure taxonomy from KB-07."""

    L1_GENERATION = "L1_GENERATION"          # hallucination / bad output
    L2_INFORMATION = "L2_INFORMATION"         # missing tool or knowledge
    L3_COORDINATION = "L3_COORDINATION"       # agent loop / deadlock
    L4_GOAL_DRIFT = "L4_GOAL_DRIFT"           # objective shifted from proposal


# ---------------------------------------------------------------------------
# Sub-schemas (Pydantic for validation at boundaries)
# ---------------------------------------------------------------------------


class ResearchProposal(BaseModel):
    title: str
    hypothesis: str
    success_metric: str = Field(description="Quantitative, e.g. 'top-1 acc > 85% on CIFAR-10'")
    baseline_paper: str = Field(description="Specific paper + number to beat")
    baseline_score: float
    novelty_assessment: str
    sentinel_anomaly_schema: dict


class ExperimentResults(BaseModel):
    run_id: str
    metric_name: str
    metric_value: float
    metric_source: str = Field(description="Path to trainer_state.json or CSVLogger file")
    hyperparameters: dict
    code_path: str
    docker_image: str
    completed_at: datetime


class PaperDraft(BaseModel):
    latex_path: str
    abstract: str
    run_id: str
    generated_at: datetime


class ValidationReport(BaseModel):
    status: ReviewStatus
    stage_reached: ReviewerStage
    scores: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    human_note: str | None = None


class EvolutionSignal(BaseModel):
    """3D composite signal for DSPy+GEPA optimizer (KB-07)."""

    reproducibility_pass_rate: float   # fraction of golden dataset traces that pass
    execution_stability_score: float   # 1 - (std_dev / mean) of experiment runtime
    reviewer_quality_rubric: float     # rolling average of Reviewer PASS scores
    computed_at: datetime


# ---------------------------------------------------------------------------
# Main State
# ---------------------------------------------------------------------------


class AIScientistState(TypedDict):
    # --- Conversation / messages (LangGraph standard) ---
    messages: Annotated[list, add_messages]

    # --- Research core ---
    research_proposal: ResearchProposal | None
    experiment_results: ExperimentResults | None
    paper_draft: PaperDraft | None

    # --- Reviewer pipeline ---
    validation_report: ValidationReport | None
    reviewer_stage: ReviewerStage

    # --- Control flow ---
    pregel_step_count: int        # circuit breaker checks this each super-step
    failure_count: int            # experiment container failures
    human_review_pending: bool    # True when PARTIAL_FAIL awaits interrupt()

    # --- Self-evolution ---
    evolution_signal: EvolutionSignal | None
    last_gepa_run: datetime | None

    # --- Tracking ---
    session_id: str
    git_commit_hash: str          # checkpointed after each decision node
    error_log: list[str]
    failure_tier: FailureTier | None


# ---------------------------------------------------------------------------
# Reducers (pure functions — nodes call these, never mutate state directly)
# ---------------------------------------------------------------------------


def increment_pregel_step(state: AIScientistState) -> dict:
    return {"pregel_step_count": state["pregel_step_count"] + 1}


def increment_failure_count(state: AIScientistState) -> dict:
    return {"failure_count": state["failure_count"] + 1}


def append_error(state: AIScientistState, message: str) -> dict:
    return {"error_log": [*state["error_log"], message]}


def set_human_review_pending(pending: bool) -> dict:
    return {"human_review_pending": pending}


# ---------------------------------------------------------------------------
# Initial state factory
# ---------------------------------------------------------------------------


def initial_state(session_id: str) -> AIScientistState:
    """Return a clean initial state for a new research session."""
    return AIScientistState(
        messages=[],
        research_proposal=None,
        experiment_results=None,
        paper_draft=None,
        validation_report=None,
        reviewer_stage=ReviewerStage.NOT_STARTED,
        pregel_step_count=0,
        failure_count=0,
        human_review_pending=False,
        evolution_signal=None,
        last_gepa_run=None,
        session_id=session_id,
        git_commit_hash="",
        error_log=[],
        failure_tier=None,
    )
