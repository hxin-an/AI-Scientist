"""
Runtime settings loaded from environment variables.

All values have sensible defaults for local development.
Production overrides via environment variables or a .env file.

Usage:
    from ai_scientist.config.settings import settings
    print(settings.postgres_url)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- PostgreSQL (local, see OQ-04 decision) ---
    postgres_url: str = "postgresql://ai_scientist:ai_scientist@localhost:5432/ai_scientist"

    # --- Claude API ---
    anthropic_api_key: str = ""
    claude_sonnet_model: str = "claude-sonnet-4-6"
    claude_haiku_model: str = "claude-haiku-4-5-20251001"

    # --- Sentinel (local Qwen 2.5 Coder, same machine) ---
    sentinel_model_dir: str = "./models/sentinel"
    sentinel_backend: str = "llama.cpp"  # or "exllamav2"

    # --- S2AG / Literature ---
    semantic_scholar_api_key: str = ""
    openalex_email: str = ""  # polite pool

    # --- DeepReviewer ---
    deep_reviewer_model: str = "WestlakeNLP/DeepReviewer-14B"
    deep_reviewer_mode: str = "fast"  # fast | standard | best

    # --- Docker ---
    experiment_docker_image: str = "ai-scientist-experiment:latest"
    docker_gpus: str = "all"

    # --- Monitoring ---
    prometheus_port: int = 9090
    health_port: int = 8080

    # --- Paths ---
    experiments_dir: str = "./experiments"
    golden_datasets_dir: str = "./tests/golden_datasets"


settings = Settings()
