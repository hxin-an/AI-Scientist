# Changelog

All notable changes to this project will be documented in this file.
Format: [Conventional Commits](https://www.conventionalcommits.org/)

---

## [Unreleased]

### Added
- Initial project scaffold (harness, config, CI)
- `config/constants.py`: 27 named constants with KB source annotations
- `config/settings.py`: Pydantic Settings for runtime configuration
- `harness/state.py`: LangGraph TypedDict + Pydantic sub-schemas + reducers
- `harness/circuit_breaker.py`: [IMMUTABLE] Pregel super-step hard limit (15)
- `harness/hooks.py`: [IMMUTABLE] PreToolUse firewall + immutable file protection
- `harness/graph.py`: Graph assembly entry point + PostgresSaver + routing
- `docs/architecture/system_design.md`: Full system design document
- `CLAUDE.md`: Claude harness operating manual
- GitHub Actions CI with real PostgreSQL integration tests
- pre-commit hooks (ruff + mypy --strict)
