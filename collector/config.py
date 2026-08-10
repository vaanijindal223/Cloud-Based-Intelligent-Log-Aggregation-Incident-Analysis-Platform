from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql://loguser:logpass123@localhost:5432/logaggregator"
    aws_region: str = "us-east-1"
    log_group_name: str = "/log-aggregator/application"
    # CloudWatch is the production source. Local reads the simulator's shared
    # JSONL file during development without AWS credentials.
    log_source: str = "local"
    local_log_file: str = "/var/log/log-aggregator/application.log"

    poll_interval_seconds: int = 10
    # Re-fetch a small window behind the last stored timestamp so an event that
    # arrived at CloudWatch slightly out of order isn't missed at the boundary.
    # source_event_id's unique constraint makes re-fetching safe.
    overlap_seconds: int = 5
    # How far back to look on a cold start (empty logs table).
    initial_lookback_seconds: int = 3600


settings = Settings()
