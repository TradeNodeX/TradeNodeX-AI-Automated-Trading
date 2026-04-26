import argparse
import asyncio
import os
import sys

import httpx


def headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


async def assert_status(response: httpx.Response, expected: int, label: str) -> dict:
    if response.status_code != expected:
        raise AssertionError(f'{label}: expected HTTP {expected}, got {response.status_code}: {response.text}')
    if response.headers.get('content-type', '').startswith('application/json'):
        return response.json()
    return {'text': response.text}


async def main() -> int:
    parser = argparse.ArgumentParser(description='TradeNodeX AAT release-candidate API smoke test.')
    parser.add_argument('--api-base', default=os.getenv('TRADENODEX_AAT_API_BASE', 'http://127.0.0.1:8000'))
    parser.add_argument('--operator-token', default=os.getenv('TRADENODEX_AAT_OPERATOR_TOKEN'))
    parser.add_argument('--symbol', default='BTCUSDT')
    args = parser.parse_args()
    if not args.operator_token:
        print('ERROR: operator token is required. Set TRADENODEX_AAT_OPERATOR_TOKEN or pass --operator-token.', file=sys.stderr)
        return 2
    h = headers(args.operator_token)
    async with httpx.AsyncClient(timeout=30) as client:
        print('1. health')
        health = await assert_status(await client.get(f'{args.api_base}/v1/health'), 200, 'health')
        assert health['ok'] is True
        print(health)

        print('2. legal')
        legal = await assert_status(await client.get(f'{args.api_base}/v1/legal'), 200, 'legal')
        assert legal['owner'] == 'TradeNodeX'
        assert legal['license'] == 'MIT'
        print(legal)

        print('3. dashboard')
        dashboard = await assert_status(await client.get(f'{args.api_base}/v1/dashboard'), 200, 'dashboard')
        assert 'metrics' in dashboard and 'bots' in dashboard
        print(dashboard['metrics'])

        print('4. protected write denied without token')
        denied = await client.post(f'{args.api_base}/v1/bots', json={'name': 'Denied', 'type': 'DCA', 'exchange': 'BINANCE_FUTURES'})
        assert denied.status_code in {401, 503}
        print({'denied_status': denied.status_code})

        print('5. market snapshot')
        snapshot = await assert_status(await client.post(f'{args.api_base}/v1/market-snapshot', json={'exchange': 'BINANCE_FUTURES', 'symbol': args.symbol}, headers=h), 200, 'market snapshot')
        assert snapshot['symbol'] == args.symbol
        print(snapshot)

        print('6. account')
        account = await assert_status(await client.post(f'{args.api_base}/v1/accounts', json={'name': 'Smoke Test Account', 'exchange': 'BINANCE_FUTURES', 'environment': 'TESTNET', 'dry_run': True}, headers=h), 200, 'account')
        print(account)

        print('7. bot')
        bot = await assert_status(await client.post(f'{args.api_base}/v1/bots', json={'name': 'Smoke Test DCA', 'type': 'DCA', 'exchange': 'BINANCE_FUTURES', 'symbols': [args.symbol], 'dry_run': True, 'max_position_usdt': 20, 'risk_per_tick_usdt': 5, 'account_id': account['id']}, headers=h), 200, 'bot')
        print(bot)

        print('8. tick')
        tick = await assert_status(await client.post(f"{args.api_base}/v1/bots/{bot['id']}/tick", headers=h), 200, 'tick')
        assert tick['execution']['accepted'] is True
        print(tick)

        print('9. orders')
        orders = await assert_status(await client.get(f'{args.api_base}/v1/orders'), 200, 'orders')
        assert isinstance(orders, list)
        print({'orders_count': len(orders)})

        print('10. reconcile')
        reconcile = await assert_status(await client.post(f'{args.api_base}/v1/reconcile', headers=h), 200, 'reconcile')
        assert 'results' in reconcile
        print(reconcile)

        print('SMOKE_TEST_PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
