from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
PROJECT_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    """全局配置。所有路径都基于 backend/ 目录，避免受启动目录影响。"""

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "学业情况分析智能体"
    app_version: str = "1.2.0"
    api_prefix: str = "/api/v1"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000

    database_url: str = f"sqlite+aiosqlite:///{(DATA_DIR / 'app.db').as_posix()}"
    db_echo: bool = False

    jwt_secret: str = "dev-only-secret-change-me-32bytes-min"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24 * 7

    checkpoint_path: str = str(DATA_DIR / "checkpoints.sqlite")
    upload_dir: str = str(DATA_DIR / "uploads")
    plan_dir: str = str(DATA_DIR / "plans")
    seed_dir: str = str(DATA_DIR / "seeds")
    frontend_dist: str = str(PROJECT_DIR / "frontend" / "dist")

    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1200

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    current_term: str = "2025-2026-2"
    engine_version: str = "audit-engine/1.2.0"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())

    @property
    def plan_path(self) -> Path:
        return Path(self.plan_dir) / "CS-BT-2024-v1.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
