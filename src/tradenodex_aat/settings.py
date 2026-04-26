from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='TRADENODEX_AAT_', extra='ignore')

    db_path: str = './data/tradenodex_aat.sqlite3'
    operator_token: str = 'change-me'
    encryption_key: str | None = None
    enable_live_trading: bool = False
    default_dry_run: bool = True
    tick_seconds: int = 15
    worker_interval_seconds: int = 10
    api_base: str = 'http://127.0.0.1:8000'
    max_retry_attempts: int = 3
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    alert_webhook_url: str | None = None
    market_stream_enabled: bool = False

    def ensure_data_dir(self) -> None:
        Path(self.db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_data_dir()
    return settings
