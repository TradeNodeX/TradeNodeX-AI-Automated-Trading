from typing import Any

from .adapters import build_adapter
from .db import add_log, list_accounts, list_positions, upsert_position


async def reconcile_account(account: dict[str, Any]) -> dict[str, Any]:
    adapter = build_adapter(account['exchange'], dry_run=bool(account.get('dry_run', True)))
    remote_positions = await adapter.fetch_positions()
    stored = []
    for position in remote_positions:
        payload = {
            'account_id': account['id'],
            'exchange': account['exchange'],
            'symbol': position.get('symbol'),
            'side': position.get('side', 'NET'),
            'qty': position.get('qty', 0),
            'entry_price': position.get('entry_price'),
            'mark_price': position.get('mark_price'),
            'unrealized_pnl': position.get('unrealized_pnl'),
        }
        stored.append(upsert_position(payload))
    add_log('Position reconciliation completed', detail={'account_id': account['id'], 'exchange': account['exchange'], 'positions': len(stored)})
    return {'account_id': account['id'], 'positions': stored}


async def reconcile_all_accounts() -> dict[str, Any]:
    results = []
    for account in list_accounts():
        results.append(await reconcile_account(account))
    return {'accounts': len(results), 'results': results, 'local_positions': list_positions()}
