"""Configuration management using Pydantic Settings."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Devin API settings
    devin_api_key: str
    devin_github_secret_id: str
    devin_api_base_url: str = "https://api.devin.ai/v1"

    # GitHub settings
    github_webhook_secret: str
    github_token: str = ""  # Optional: for posting comments on PRs
    target_bot_usernames: List[str] = ["Code-Rabbit-App", "cursor-bug-bot"]

    # Repository settings
    session_db_path: str = "data/pending_sessions.json"

    # Monitor settings
    monitor_poll_interval: int = 30  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
