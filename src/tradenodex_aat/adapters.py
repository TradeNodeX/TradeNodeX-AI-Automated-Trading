import hashlib
import json
from typing import Any

from .exchanges import get_exchange_spec


class ExchangeAdapterError(RuntimeError):
    pass


class BaseExchangeAdapter:
    def __init__(self, exchange: str, dry_run: bool = True) -> None:
        self.exchange = exchange
        self.spec = get_exchange_spec(exchange)
        self.dry_run = dry_run

    def make_idempotency_key(self, bot_id: str, order: dict[str, Any]) -> str:
        basis = json.dumps({'bot_id': bot_id, 'exchange': self.exchange, 'order': order}, sort_keys=True)
        return hashlib.sha256(basis.encode('utf-8')).hexdigest()

    async def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'exchange': self.exchange, 'status': 'ACCEPTED_DRY_RUN', 'order': order}
        return await self.place_live_order(order)

    async def place_live_order(self, order: dict[str, Any]) -> dict[str, Any]:
        raise ExchangeAdapterError('Live native execution adapter is not enabled until credentials, testnet and risk gates are validated.')

    async def fetch_positions(self) -> list[dict[str, Any]]:
        return []

    async def fetch_market_snapshot(self, symbol: str) -> dict[str, Any]:
        return {'exchange': self.exchange, 'symbol': symbol, 'mark_price': 50000.0, 'funding_rate': 0.0, 'source': 'adapter-fallback'}


class CcxtExchangeAdapter(BaseExchangeAdapter):
    async def place_live_order(self, order: dict[str, Any]) -> dict[str, Any]:
        raise ExchangeAdapterError('CCXT live order placement requires credential-vault wiring and exchange-specific testnet validation before enabling.')


def build_adapter(exchange: str, dry_run: bool = True) -> BaseExchangeAdapter:
    return CcxtExchangeAdapter(exchange, dry_run=dry_run)
