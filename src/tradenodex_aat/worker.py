import asyncio
import os

import httpx

API_BASE = os.getenv('TRADENODEX_AAT_API_BASE', 'http://127.0.0.1:8000')
INTERVAL_SECONDS = float(os.getenv('TRADENODEX_AAT_WORKER_INTERVAL_SECONDS', '10'))
MARKET_STREAM_ENABLED = os.getenv('TRADENODEX_AAT_MARKET_STREAM_ENABLED', 'false').lower() == 'true'
RECONCILE_EVERY_TICKS = int(os.getenv('TRADENODEX_AAT_RECONCILE_EVERY_TICKS', '6'))
OPERATOR_TOKEN = os.getenv('TRADENODEX_AAT_OPERATOR_TOKEN', '')


def auth_headers() -> dict[str, str]:
    return {'Authorization': f'Bearer {OPERATOR_TOKEN}'} if OPERATOR_TOKEN else {}


async def run_once(client: httpx.AsyncClient, tick_index: int) -> None:
    dashboard = (await client.get(f'{API_BASE}/v1/dashboard')).json()
    pairs: set[tuple[str, str]] = set()
    for bot in dashboard.get('bots', []):
        symbols = bot.get('symbols') or []
        for symbol in symbols:
            pairs.add((bot['exchange'], symbol))
        if bot.get('status') == 'RUNNING':
            await client.post(f"{API_BASE}/v1/bots/{bot['id']}/tick", headers=auth_headers())
    if MARKET_STREAM_ENABLED:
        for exchange, symbol in sorted(pairs):
            await client.post(f'{API_BASE}/v1/market-snapshot', json={'exchange': exchange, 'symbol': symbol}, headers=auth_headers())
    if tick_index % RECONCILE_EVERY_TICKS == 0:
        await client.post(f'{API_BASE}/v1/reconcile', headers=auth_headers())


async def main() -> None:
    tick_index = 0
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            tick_index += 1
            try:
                await run_once(client, tick_index)
            except Exception as exc:
                print(f'[TradeNodeX AAT worker] loop failed: {exc}')
            await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == '__main__':
    asyncio.run(main())
