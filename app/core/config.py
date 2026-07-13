from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "postgresql+psycopg://polymarket:polymarket@localhost:5432/polymarket"
    redis_url: str = "redis://localhost:6379/0"
    admin_api_key: str = Field(default="change-me")

    gamma_base_url: str = "https://gamma-api.polymarket.com"
    data_api_base_url: str = "https://data-api.polymarket.com"
    clob_base_url: str = "https://clob.polymarket.com"
    polymarket_subgraph_url: str | None = None
    polygon_rpc_url: str | None = None
    bitquery_api_key: str | None = None

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    pushplus_token: str | None = None

    http_timeout_seconds: float = 25
    http_max_retries: int = 4
    default_rate_limit_per_minute: int = 90
    enable_scheduler: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()

