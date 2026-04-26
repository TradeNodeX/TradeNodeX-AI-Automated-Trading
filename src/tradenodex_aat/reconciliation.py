from typing import Any

from .adapters import build_adapter
from .credentials import load_account_credentials
from .db import add_log, list_accounts, list_positions, upsert_balance, upsert_open_order, upsert_position


async def reconcile_account(account: dict[str, Any]) -> dict[str, Any]:
    credentials = load_account_credentials(account.get('id'), account['exchange'], account.get('environment', 'TESTNET'))
    adapter = build_adapter(account['exchange'], dry_run=bool(account.get('dry_run', True)), credentials=credentials, account=account)
    remote_positions = await adapter.fetch_positions()
    remote_orders = await adapter.fetch_open_orders()
    remote_balance = await adapter.fetch_balance()
    positions = []
    open_orders = []
    balances = []
    for position in remote_positions:
        positions.append(upsert_position({'account_id': account['id'], 'exchange': account['exchange'], 'symbol': position.get('symbol'), 'side': position.get('side', 'NET'), 'qty': position.get('qty', 0), 'entry_price': position.get('entry_price'), 'mark_price': position.get('mark_price'), 'unrealized_pnl': position.get('unrealized_pnl')}))
    for order in remote_orders:
        open_orders.append(upsert_open_order({'account_id': account['id'], 'exchange': account['exchange'], **order}))
    for asset, row in remote_balance.items():
        if asset == 'raw' or not isinstance(row, dict):
            continue
        balances.append(upsert_balance({'account_id': account['id'], 'exchange': account['exchange'], 'asset': asset, 'free': row.get('free'), 'total': row.get('total'), 'used': row.get('used')}))
    result = {'account_id': account['id'], 'exchange': account['exchange'], 'environment': account.get('environment'), 'dry_run': account.get('dry_run'), 'positions': positions, 'open_orders': open_orders, 'balances': balances}
    add_log('Account reconciliation completed', detail={'account_id': account['id'], 'exchange': account['exchange'], 'environment': account.get('environment'), 'positions': len(positions), 'open_orders': len(open_orders), 'balances': len(balances)})
    return result


async def reconcile_all_accounts() -> dict[str, Any]:
    results = []
    for account in list_accounts():
        results.append(await reconcile_account(account))
    return {'accounts': len(results), 'results': results, 'local_positions': list_positions()}
