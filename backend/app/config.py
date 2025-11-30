from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    twitch_bot_username: str
    twitch_oauth_token: str
    twitch_channel: str
    stonks_keyword: str = "STONKS"
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db_name: str = "stonksdb"
    tick_interval_seconds: float = 2.0
    initial_price: float = 100.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )


settings = Settings()
