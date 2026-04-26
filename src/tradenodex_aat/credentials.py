import os
from dataclasses import dataclass

from .crypto import decrypt_secret
from .db import connect


@dataclass(frozen=True)
class ExchangeCredentials:
    api_key: str | None
    api_secret: str | None
    api_passphrase: str | None = None
    environment: str = 'TESTNET'

    @property
    def ready(self) -> bool:
        return bool(self.api_key and self.api_secret)


def _env_name(exchange: str, environment: str, suffix: str) -> str:
    return f'TRADENODEX_AAT_{exchange}_{environment}_{suffix}'.upper()


def load_env_credentials(exchange: str, environment: str = 'TESTNET') -> ExchangeCredentials:
    return ExchangeCredentials(
        api_key=os.getenv(_env_name(exchange, environment, 'API_KEY')),
        api_secret=os.getenv(_env_name(exchange, environment, 'API_SECRET')),
        api_passphrase=os.getenv(_env_name(exchange, environment, 'API_PASSPHRASE')),
        environment=environment,
    )


def load_account_credentials(account_id: str | None, exchange: str, fallback_environment: str = 'TESTNET') -> ExchangeCredentials:
    if account_id:
        with connect() as conn:
            row = conn.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
        if row:
            creds = ExchangeCredentials(
                api_key=decrypt_secret(row['api_key_encrypted']),
                api_secret=decrypt_secret(row['api_secret_encrypted']),
                api_passphrase=decrypt_secret(row['api_passphrase_encrypted']),
                environment=row['environment'],
            )
            if creds.ready:
                return creds
            return load_env_credentials(exchange, row['environment'] or fallback_environment)
    return load_env_credentials(exchange, fallback_environment)
