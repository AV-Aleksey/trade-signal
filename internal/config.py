"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    LOG_LEVEL: str = "INFO"
    API_BOT_KEY: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
