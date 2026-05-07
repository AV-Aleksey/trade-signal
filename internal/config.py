from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    ITICK_API_KEY: str = ""
    ITICK_ENVIRONMENT: str = "DEV"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
