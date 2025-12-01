from __future__ import annotations

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    twitch_bot_username: str
    twitch_oauth_token: str
    twitch_channel: str
    twitch_client_id: str
    twitch_client_secret: str
    stonks_up_keyword: str = "STONKS"
    stonks_down_keyword: str = "STONKS DOWN"
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db_name: str = "stonksdb"
    allowed_origins: List[str] = Field(default_factory=list)
    tick_interval_minutes: float = 30.0
    initial_price: float = 100.0

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            parts = [origin.strip() for origin in value.split(",") if origin.strip()]
            return parts
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )


settings = Settings()
