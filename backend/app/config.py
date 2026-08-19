"""Central app settings, read from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_mode: str = "stub"  # "live" | "stub"
    openai_api_key: str = ""
    openai_base_url: str = "https://openrouter.ai/api/v1"
    openai_model: str = "openai/gpt-oss-20b:free"
    llm_max_calls_per_investigation: int = 8
    llm_timeout_seconds: int = 45

    # Qdrant
    qdrant_url: str = ""
    qdrant_path: str = str(BACKEND_DIR / "data_out" / "qdrant")
    qdrant_collection: str = "network_knowledge"

    # Embeddings
    embedding_backend: str = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # MLflow
    mlflow_tracking_uri: str = str(BACKEND_DIR / "mlruns")
    mlflow_experiment: str = "network-intelligence-copilot"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    data_seed: int = 42

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def data_out_dir(self) -> Path:
        d = BACKEND_DIR / "data_out"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def knowledge_dir(self) -> Path:
        return BACKEND_DIR / "knowledge"


@lru_cache
def get_settings() -> Settings:
    return Settings()
