import asyncio
import json
from typing import Any

from .adapters import build_adapter
from .alerts import notify_execution_event
from .credentials import load_account_credentials
from .db import add_log, insert_order, update_order
from .risk import pre_trade_risk_check
from .settings import get_settings


async def execute_strategy_orders_release(bot: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    checked = pre_trade_risk_check(bot, decision.get('orders') or [], live_enabled=settings.enable_live_trading)
    if not checked.allowed:
        add_log('Pre-trade risk rejected orders', level='WARN', bot_id=bot['id'], detail={'reason': checked.reason})
        await notify_execution_event('TradeNodeX risk rejection', {'bot_id': bot['id'], 'reason': checked.reason})
        return {'accepted': False, 'reason': checked.reason, 'orders': []}
    dry_run = bool(bot.get('dry_run', True))
    creds = load_account_credentials(bot.get('account_id'), bot['exchange'], 'TESTNET')
    adapter = build_adapter(bot['exchange'], dry_run=dry_run, credentials=creds)
    results = []
    for src in checked.normalized_orders:
        symbol = src.get('symbol') or decision.get('symbol') or (bot.get('symbols') or ['BTCUSDT'])[0]
        order = {'symbol': symbol, 'side': src['side'], 'type': src.get('type') or 'LIMIT', 'qty': src['qty'], 'price': src.get('price'), 'post_only': bool(src.get('post_only', False)), 'reduce_only': bool(src.get('reduce_only', False)), 'reference_price': src.get('reference_price')}
        idem = adapter.make_idempotency_key(bot['id'], order)
        client_id = f"tnx{bot['id'].replace('-', '')[:10]}{idem[:20]}"[:36]
        order['client_order_id'] = client_id
        stored = insert_order({'bot_id': bot['id'], 'idempotency_key': idem, 'exchange': bot['exchange'], 'symbol': symbol, 'side': order['side'], 'order_type': order['type'], 'qty': order['qty'], 'price': order.get('price'), 'status': 'PENDING'})
        if stored.get('status') in {'FILLED', 'ACCEPTED_DRY_RUN', 'SENT'}:
            results.append({'idempotency_key': idem, 'client_order_id': client_id, 'status': 'SKIPPED_DUPLICATE'})
            continue
        if not dry_run:
            remote = await adapter.fetch_order_by_client_id(symbol, client_id)
            if remote:
                update_order(stored['id'], {'status': remote.get('status', 'SENT'), 'raw_response_json': json.dumps(remote), 'last_error': None})
                results.append({'idempotency_key': idem, 'client_order_id': client_id, 'status': 'REMOTE_SYNCED'})
                continue
        last_error = None
        for attempt in range(1, settings.max_retry_attempts + 1):
            try:
                response = await adapter.place_order(order)
                status = response.get('status', 'SENT')
                update_order(stored['id'], {'status': status, 'attempts': attempt, 'raw_response_json': json.dumps(response), 'last_error': None})
                result = {'idempotency_key': idem, 'client_order_id': client_id, 'status': status, 'attempts': attempt}
                results.append(result)
                await notify_execution_event('TradeNodeX order event', {'bot_id': bot['id'], 'result': result})
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)
                if not dry_run:
                    remote = await adapter.fetch_order_by_client_id(symbol, client_id)
                    if remote:
                        update_order(stored['id'], {'status': remote.get('status', 'SENT'), 'attempts': attempt, 'raw_response_json': json.dumps(remote), 'last_error': None})
                        results.append({'idempotency_key': idem, 'client_order_id': client_id, 'status': 'REMOTE_SYNCED_AFTER_ERROR', 'attempts': attempt})
                        last_error = None
                        break
                update_order(stored['id'], {'status': 'RETRYING' if attempt < settings.max_retry_attempts else 'FAILED', 'attempts': attempt, 'last_error': last_error})
                if attempt < settings.max_retry_attempts:
                    await asyncio.sleep(min(2 ** attempt, 8))
        if last_error:
            failure = {'idempotency_key': idem, 'client_order_id': client_id, 'status': 'FAILED', 'error': last_error}
            results.append(failure)
            await notify_execution_event('TradeNodeX order failure', {'bot_id': bot['id'], 'failure': failure})
    add_log('Release execution pipeline completed', bot_id=bot['id'], detail={'decision_action': decision.get('action'), 'results': results})
    return {'accepted': True, 'reason': checked.reason, 'orders': results}
