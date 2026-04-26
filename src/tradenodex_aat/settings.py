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
    reconcile_every_ticks: int = 6
    api_base: str = 'http://127.0.0.1:8000'
    max_retry_attempts: int = 3
    market_stream_enabled: bool = False
    rate_limit_per_minute: int = 60
    allowed_origins: str = 'http://127.0.0.1:8000,http://localhost:8000'
    binance_testnet_default_leverage: int = 1
    binance_testnet_margin_mode: str = 'ISOLATED'
    binance_mainnet_default_leverage: int = 1
    binance_mainnet_margin_mode: str = 'ISOLATED'
    global_max_order_notional_usdt: float = 100
    global_daily_loss_limit_usdt: float = 50
    copy_engine_enabled: bool = True
    copy_primary_account_id: str | None = None
    copy_default_symbol: str = 'BTCUSDT'
    copy_default_notional_usdt: float = 5
    copy_max_signal_queue_size: int = 5000
    copy_max_concurrent_executions: int = 4
    copy_max_slippage_bps: float = 30
    copy_default_multiplier: float = 1.0
    copy_user_stream_enabled: bool = False
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    alert_webhook_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None

    def ensure_data_dir(self) -> None:
        Path(self.db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    @property
    def origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(',') if item.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_data_dir()
    return settings
