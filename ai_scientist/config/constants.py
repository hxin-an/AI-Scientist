"""
All named constants for the AI Scientist system.

Rule: NO magic numbers anywhere else in the codebase.
      Import from here. Never hardcode thresholds inline.

Sources documented per constant (KB reference or requirements.md).
"""

# ---------------------------------------------------------------------------
# LangGraph / Orchestration  (source: KB-07, KB-01)
# ---------------------------------------------------------------------------

#: Hard upper bound on Pregel super-steps. Circuit breaker fires at this limit.
MAX_PREGEL_SUPER_STEPS: int = 15

#: Maximum times an experiment container may fail before escalating to human.
MAX_EXPERIMENT_RETRIES: int = 4

# ---------------------------------------------------------------------------
# Context Window Management  (source: KB-09)
# ---------------------------------------------------------------------------

#: Above this fraction of context used, delegate to a sub-agent.
#: Known as the "dumb zone" threshold from Anthropic infrastructure study.
CONTEXT_DUMB_ZONE_THRESHOLD: float = 0.40

# ---------------------------------------------------------------------------
# Reviewer Pipeline  (source: KB-10, KB-08)
# ---------------------------------------------------------------------------

#: DeepReviewer-14B Fast Mode score below this → CRITICAL_FAIL.
DEEP_REVIEWER_CRITICAL_THRESHOLD: float = 4.0

#: DeepReviewer-14B Fast Mode score in [critical, partial] → PARTIAL_FAIL.
DEEP_REVIEWER_PARTIAL_THRESHOLD: float = 6.0

#: MVVC cosine similarity above this → derivative work → CRITICAL_FAIL.
MVVC_SIMILARITY_CRITICAL: float = 0.98

#: MVVC Sentinel single-shot score below this → CRITICAL_FAIL.
MVVC_SENTINEL_SCORE_MIN: int = 3

#: S2AG SPECTER2 cosine distance "sweet spot" lower bound.
#: Below this → too close to existing work.
S2AG_COSINE_SWEET_SPOT_LOW: float = 0.60

#: S2AG SPECTER2 cosine distance "sweet spot" upper bound.
#: Above this → too far from established field (speculative).
S2AG_COSINE_SWEET_SPOT_HIGH: float = 0.85

#: Empirical Supremacy: if absolute delta over SOTA exceeds this,
#: override any LLM-generated CRITICAL_FAIL to PARTIAL_FAIL (human escalation).
EMPIRICAL_SUPREMACY_THRESHOLD: float = 0.15

# ---------------------------------------------------------------------------
# Statistical Validation  (source: KB-08)
# ---------------------------------------------------------------------------

#: Minimum experiment runs by domain before statistical tests are valid.
MIN_RUNS_CV: int = 5         # Computer Vision
MIN_RUNS_NLP: int = 5        # Natural Language Processing (up to 10 recommended)
MIN_RUNS_RL: int = 10        # Reinforcement Learning (up to 20 recommended)

#: Benjamini-Hochberg FDR correction significance level.
STATISTICAL_ALPHA: float = 0.05

# ---------------------------------------------------------------------------
# Self-Evolution  (source: KB-07)
# ---------------------------------------------------------------------------

#: Rolling window for Reviewer score trend detection.
EVOLUTION_ROLLING_WINDOW: int = 5

#: Minimum improvement on golden dataset regression before accepting a mutation.
GEPA_REGRESSION_MIN_IMPROVEMENT: float = 0.02

# ---------------------------------------------------------------------------
# Auto-Rollback  (source: requirements.md)
# ---------------------------------------------------------------------------

#: Trigger git revert if Reviewer score rolling avg drops by this fraction.
ROLLBACK_REVIEWER_SCORE_DROP: float = 0.05

#: Number of consecutive drops before rollback fires.
ROLLBACK_CONSECUTIVE_DROPS: int = 3

# ---------------------------------------------------------------------------
# Sentinel / VRAM  (source: KB-03)
# ---------------------------------------------------------------------------

#: Maximum fraction of total GPU VRAM allocated to Sentinel model.
#: Remaining VRAM is reserved for ML experiments.
SENTINEL_VRAM_BUDGET_RATIO: float = 0.20

#: Hard VRAM buffer kept free for system and experiment overhead (GB).
EXPERIMENT_VRAM_RESERVE_GB: float = 2.0

#: DCGM GPU memory utilisation alert threshold (fraction).
DCGM_MEMORY_ALERT_THRESHOLD: float = 0.90

#: DCGM GPU temperature alert threshold (Celsius).
DCGM_TEMPERATURE_ALERT_CELSIUS: float = 85.0

# ---------------------------------------------------------------------------
# Monitoring  (source: requirements.md)
# ---------------------------------------------------------------------------

#: Prometheus metrics scrape port.
PROMETHEUS_PORT: int = 9090

#: Health endpoint port.
HEALTH_PORT: int = 8080

#: Token cost velocity alert — USD per hour.
TOKEN_COST_VELOCITY_ALERT_USD_PER_HOUR: float = 5.0

#: Minimum acceptable tool cache hit rate before alerting.
TOOL_CACHE_HIT_RATE_MIN: float = 0.50
