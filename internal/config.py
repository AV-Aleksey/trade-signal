from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"

    ITICK_API_KEY: str = ""
    ITICK_ENVIRONMENT: str = "DEV"
    TOKEN_ENCRYPTION_SECRET: str = ""
    SQLITE_DB_PATH: str = "./data/trade_signal.db"

    BOT_API_KEY: str = ""

    OPEN_ROUTER_API_KEY: str = Field(
        default="",
        validation_alias="open_router",
    )

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
