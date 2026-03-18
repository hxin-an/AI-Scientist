# AI Scientist

Automated Deep Learning research pipeline: from idea to paper draft,
with minimal human intervention and self-evolution capability.

## Status

🚧 Phase 1 — Infrastructure scaffold in progress

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (package manager)
- PostgreSQL 16+ (local)
- Docker + NVIDIA GPU (RTX 30/40/90 series)
- WSL2 (Windows) or Linux (Ubuntu 22.04+)

## Quick Start

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and PostgreSQL URL

# Run tests
uv run pytest
```

## Architecture

See [docs/architecture/system_design.md](docs/architecture/system_design.md) for full system design.

Key components:
- **Harness** — LangGraph graph, State schema, circuit breaker, hooks
- **Agents** — Planner, Researcher, Writer (LangGraph nodes)
- **Reviewer** — 5-stage research value pipeline (Statistical → MVVC → DeepReviewer → S2AG → Empirical Supremacy)
- **Sentinel** — Local Qwen 2.5 Coder for monitoring (same machine, VRAM-tiered)
- **Evolution** — DSPy + GEPA prompt optimization

## Development

```bash
# Lint + format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy --strict ai_scientist/

# Tests (requires running PostgreSQL)
uv run pytest
```

CI runs on every push and PR via GitHub Actions.
