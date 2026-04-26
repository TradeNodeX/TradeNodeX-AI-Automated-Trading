import asyncio
import json
from typing import Any

from .adapters import build_adapter
from .db import add_log, insert_order, update_order
from .risk import pre_trade_risk_check
from .settings import get_settings


async def execute_strategy_orders(bot: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    orders = decision.get('orders') or []
    risk = pre_trade_risk_check(bot, orders, live_enabled=settings.enable_live_trading)
    if not risk.allowed:
        add_log('Pre-trade risk rejected orders', level='WARN', bot_id=bot['id'], detail={'reason': risk.reason})
        return {'accepted': False, 'reason': risk.reason, 'orders': []}

    adapter = build_adapter(bot['exchange'], dry_run=bool(bot.get('dry_run', True)))
    results = []
    for order in risk.normalized_orders:
        exchange_order = {
            'symbol': decision.get('symbol') or (bot.get('symbols') or ['BTCUSDT'])[0],
            'side': order['side'],
            'type': order.get('type') or order.get('order_type') or 'LIMIT',
            'qty': order['qty'],
            'price': order.get('price'),
            'reduce_only': bool(order.get('reduce_only', False)),
            'post_only': bool(order.get('post_only', False)),
        }
        idempotency_key = adapter.make_idempotency_key(bot['id'], exchange_order)
        stored = insert_order({
            'bot_id': bot['id'],
            'idempotency_key': idempotency_key,
            'exchange': bot['exchange'],
            'symbol': exchange_order['symbol'],
            'side': exchange_order['side'],
            'order_type': exchange_order['type'],
            'qty': exchange_order['qty'],
            'price': exchange_order.get('price'),
            'status': 'PENDING',
        })
        if stored.get('status') in {'FILLED', 'ACCEPTED_DRY_RUN', 'SENT'}:
            results.append({'idempotency_key': idempotency_key, 'status': 'SKIPPED_DUPLICATE', 'order_id': stored['id']})
            continue
        attempt = 0
        last_error = None
        while attempt < settings.max_retry_attempts:
            attempt += 1
            try:
                response = await adapter.place_order(exchange_order)
                status = response.get('status', 'SENT')
                update_order(stored['id'], {'status': status, 'attempts': attempt, 'raw_response_json': json.dumps(response), 'last_error': None})
                results.append({'idempotency_key': idempotency_key, 'status': status, 'attempts': attempt, 'response': response})
                break
            except Exception as exc:
                last_error = str(exc)
                update_order(stored['id'], {'status': 'RETRYING' if attempt < settings.max_retry_attempts else 'FAILED', 'attempts': attempt, 'last_error': last_error})
                if attempt < settings.max_retry_attempts:
                    await asyncio.sleep(min(2 ** attempt, 8))
        if last_error and attempt >= settings.max_retry_attempts:
            results.append({'idempotency_key': idempotency_key, 'status': 'FAILED', 'attempts': attempt, 'error': last_error})
    add_log('Execution pipeline completed', bot_id=bot['id'], detail={'decision_action': decision.get('action'), 'results': results})
    return {'accepted': True, 'reason': risk.reason, 'orders': results}
