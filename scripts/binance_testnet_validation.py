import argparse
import asyncio
import os
import sys

import httpx


async def main() -> int:
    parser = argparse.ArgumentParser(description='TradeNodeX Binance Futures Testnet validation helper.')
    parser.add_argument('--api-base', default=os.getenv('TRADENODEX_AAT_API_BASE', 'http://127.0.0.1:8000'))
    parser.add_argument('--symbol', default='BTCUSDT')
    parser.add_argument('--max-position-usdt', type=float, default=20)
    parser.add_argument('--risk-per-tick-usdt', type=float, default=5)
    parser.add_argument('--place-test-order', action='store_true', help='Create a non-dry-run testnet bot and call tick. Requires live gate enabled and testnet credentials configured.')
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=30) as client:
        health = (await client.get(f'{args.api_base}/v1/health')).json()
        print('health:', health)
        snap = (await client.post(f'{args.api_base}/v1/market-snapshot', json={'exchange': 'BINANCE_FUTURES', 'symbol': args.symbol})).json()
        print('market_snapshot:', snap)
        account_payload = {
            'name': 'Binance Futures Testnet Validation',
            'exchange': 'BINANCE_FUTURES',
            'environment': 'TESTNET',
            'base_currency': 'USDT',
            'dry_run': not args.place_test_order,
        }
        account = (await client.post(f'{args.api_base}/v1/accounts', json=account_payload)).json()
        print('account:', account)
        bot_payload = {
            'name': 'Binance Testnet Validation DCA',
            'type': 'DCA',
            'exchange': 'BINANCE_FUTURES',
            'symbols': [args.symbol],
            'dry_run': not args.place_test_order,
            'max_position_usdt': args.max_position_usdt,
            'risk_per_tick_usdt': args.risk_per_tick_usdt,
            'account_id': account['id'],
        }
        bot = (await client.post(f'{args.api_base}/v1/bots', json=bot_payload)).json()
        print('bot:', bot)
        tick = (await client.post(f"{args.api_base}/v1/bots/{bot['id']}/tick")).json()
        print('tick:', tick)
        reconcile = (await client.post(f'{args.api_base}/v1/reconcile')).json()
        print('reconcile:', reconcile)
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
