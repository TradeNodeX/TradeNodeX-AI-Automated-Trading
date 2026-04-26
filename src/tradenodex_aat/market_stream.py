import asyncio
from typing import Iterable

from .adapters import build_adapter
from .db import add_log, store_market_snapshot


async def poll_market_snapshot(exchange: str, symbol: str) -> dict:
    adapter = build_adapter(exchange, dry_run=True)
    snapshot = await adapter.fetch_market_snapshot(symbol)
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
