import asyncio
from typing import Iterable

from .adapters import build_adapter
from .credentials import load_env_credentials
from .db import add_log, store_market_snapshot


def fallback_market_snapshot(exchange: str, symbol: str) -> dict:
    base_price = 50000.0 if symbol.startswith('BTC') else 2500.0 if symbol.startswith('ETH') else 100.0
    return {'exchange': exchange, 'symbol': symbol, 'mark_price': base_price, 'funding_rate': 0.0, 'bid': base_price * 0.9999, 'ask': base_price * 1.0001, 'source': 'dry-run-fallback'}


async def poll_market_snapshot(exchange: str, symbol: str, environment: str = 'TESTNET') -> dict:
    credentials = load_env_credentials(exchange, environment)
    if not credentials.ready:
        snapshot = fallback_market_snapshot(exchange, symbol)
    else:
        adapter = build_adapter(exchange, dry_run=True, credentials=credentials)
        try:
            snapshot = await adapter.fetch_market_snapshot(symbol)
        except Exception as exc:
            snapshot = fallback_market_snapshot(exchange, symbol)
            snapshot['source'] = f'dry-run-fallback-after-error:{type(exc).__name__}'
    stored = store_market_snapshot(snapshot)
    add_log('Market snapshot stored', detail={'exchange': exchange, 'symbol': symbol, 'source': stored['source']})
    return stored


async def run_market_poll_loop(pairs: Iterable[tuple[str, str]], interval_seconds: int = 15) -> None:
    pair_list = list(pairs)
    while True:
        for exchange, symbol in pair_list:
            try:
                await poll_market_snapshot(exchange, symbol)
            except Exception as exc:
                add_log('Market snapshot polling failed', level='WARN', detail={'exchange': exchange, 'symbol': symbol, 'error': str(exc)})
        await asyncio.sleep(interval_seconds)


class FundingRateWatcher:
    def __init__(self, threshold_abs: float = 0.0003) -> None:
        self.threshold_abs = threshold_abs

    def should_alert(self, snapshot: dict) -> bool:
        return abs(float(snapshot.get('funding_rate', 0))) >= self.threshold_abs
