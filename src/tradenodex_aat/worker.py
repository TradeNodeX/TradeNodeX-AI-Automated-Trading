import asyncio
import os

import httpx

API_BASE = os.getenv('TRADENODEX_AAT_API_BASE', 'http://127.0.0.1:8000')
INTERVAL_SECONDS = float(os.getenv('TRADENODEX_AAT_WORKER_INTERVAL_SECONDS', '10'))

async def run_once(client: httpx.AsyncClient) -> None:
    dashboard = (await client.get(f'{API_BASE}/v1/dashboard')).json()
    for bot in dashboard.get('bots', []):
        if bot.get('status') == 'RUNNING':
            await client.post(f"{API_BASE}/v1/bots/{bot['id']}/tick")

async def main() -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            try:
                await run_once(client)
            except Exception as exc:  # worker must not crash on transient exchange/API failure
                print(f'[TradeNodeX AAT worker] tick failed: {exc}')
            await asyncio.sleep(INTERVAL_SECONDS)

if __name__ == '__main__':
    asyncio.run(main())
