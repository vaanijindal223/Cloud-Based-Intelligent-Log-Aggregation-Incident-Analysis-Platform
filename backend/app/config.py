from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql://loguser:logpass123@localhost:5432/logaggregator"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
