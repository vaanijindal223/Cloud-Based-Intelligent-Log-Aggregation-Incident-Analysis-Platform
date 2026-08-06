from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql://loguser:logpass123@localhost:5432/logaggregator"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Demo log file that Phase 3's CloudWatch Agent will tail. Simulations append
    # newline-delimited JSON here; nothing in this app pushes to AWS directly.
    log_file_path: str = str(REPO_ROOT / "logs" / "application.log")


settings = Settings()
