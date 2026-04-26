import asyncio
import time
from typing import Any
from uuid import uuid4

from .account_controls import account_can_execute, record_account_execution
from .adapters import build_adapter
from .alerts import notify_execution_event
from .credentials import load_account_credentials
from .db import add_log, connect, insert_order, list_accounts, update_order
from .settings import get_settings
from .signal_bus import SIGNAL_BUS, SignalEvent, persist_execution_event


class CopyEngineError(RuntimeError):
    pass


def resolve_primary_account(signal: SignalEvent) -> dict[str, Any]:
    accounts = list_accounts()
    if signal.target_account_id:
        for account in accounts:
            if account['id'] == signal.target_account_id:
                return account
        raise CopyEngineError('target_account_not_found')
    settings = get_settings()
    if settings.copy_primary_account_id:
        for account in accounts:
            if account['id'] == settings.copy_primary_account_id:
                return account
        raise CopyEngineError('configured_primary_account_not_found')
    for account in accounts:
        if account['exchange'] == 'BINANCE_FUTURES':
            return account
    if not accounts:
        raise CopyEngineError('no_account_configured')
    return accounts[0]


def signal_to_order(signal: SignalEvent, account: dict[str, Any]) -> dict[str, Any]:
    notional = signal.notional_usdt * signal.multiplier * get_settings().copy_default_multiplier
    price = signal.price
    reference_price = price or 50000.0
    qty = round(notional / reference_price, 8)
    return {
        'symbol': signal.symbol,
        'side': signal.side,
        'type': signal.order_type,
        'qty': qty,
        'price': price,
        'reference_price': reference_price,
        'client_order_id': None,
        'post_only': False,
        'reduce_only': False,
        'account_id': account['id'],
        'notional_usdt': notional,
    }


async def execute_copy_signal(signal: SignalEvent) -> dict[str, Any]:
    started = time.perf_counter()
    account = resolve_primary_account(signal)
    order = signal_to_order(signal, account)
    allowed, reason = account_can_execute(account['id'], float(order['notional_usdt']), signal.slippage_bps)
    if not allowed:
        persist_execution_event(signal.id, 'REJECTED', account_id=account['id'], error=reason, detail={'signal': signal.raw})
        record_account_execution(account['id'], 0, error=reason)
        await notify_execution_event('TradeNodeX copy signal rejected', {'signal_id': signal.id, 'account_id': account['id'], 'reason': reason})
        return {'accepted': False, 'reason': reason, 'account_id': account['id']}
    credentials = load_account_credentials(account['id'], account['exchange'], account.get('environment', 'TESTNET'))
    dry_run = bool(account.get('dry_run', True))
    adapter = build_adapter(account['exchange'], dry_run=dry_run, credentials=credentials)
    idem = adapter.make_idempotency_key('copy-signal', {'signal_id': signal.id, 'account_id': account['id'], 'order': order})
    client_id = f"tnxcopy{idem[:24]}"[:36]
    order['client_order_id'] = client_id
    stored = insert_order({'bot_id': 'copy-engine', 'idempotency_key': idem, 'exchange': account['exchange'], 'symbol': order['symbol'], 'side': order['side'], 'order_type': order['type'], 'qty': order['qty'], 'price': order.get('price'), 'status': 'PENDING'})
    try:
        response = await adapter.place_order(order)
        status = response.get('status', 'SENT')
        latency = (time.perf_counter() - started) * 1000
        update_order(stored['id'], {'status': status, 'attempts': 1, 'raw_response_json': str(response), 'last_error': None})
        persist_execution_event(signal.id, status, account_id=account['id'], latency_ms=latency, detail={'client_order_id': client_id, 'response': response})
        record_account_execution(account['id'], float(order['notional_usdt']), latency_ms=latency)
        add_log('Copy signal executed', detail={'signal_id': signal.id, 'account_id': account['id'], 'latency_ms': latency, 'status': status})
        await SIGNAL_BUS.broadcast({'event': 'copy_executed', 'signal_id': signal.id, 'account_id': account['id'], 'status': status, 'latency_ms': latency})
        return {'accepted': True, 'signal_id': signal.id, 'account_id': account['id'], 'status': status, 'latency_ms': latency, 'client_order_id': client_id}
    except Exception as exc:
        latency = (time.perf_counter() - started) * 1000
        error = str(exc)
        update_order(stored['id'], {'status': 'FAILED', 'attempts': 1, 'last_error': error})
        persist_execution_event(signal.id, 'FAILED', account_id=account['id'], latency_ms=latency, error=error)
        record_account_execution(account['id'], float(order['notional_usdt']), latency_ms=latency, error=error)
        await notify_execution_event('TradeNodeX copy signal failed', {'signal_id': signal.id, 'account_id': account['id'], 'error': error})
        await SIGNAL_BUS.broadcast({'event': 'copy_failed', 'signal_id': signal.id, 'account_id': account['id'], 'error': error, 'latency_ms': latency})
        return {'accepted': False, 'signal_id': signal.id, 'account_id': account['id'], 'reason': error, 'latency_ms': latency}


async def run_copy_execution_worker() -> None:
    settings = get_settings()
    semaphore = asyncio.Semaphore(max(settings.copy_max_concurrent_executions, 1))
    add_log('Copy execution worker started', detail={'concurrency': settings.copy_max_concurrent_executions})
    while True:
        signal = await SIGNAL_BUS.queue.get()
        async def _run(item: SignalEvent) -> None:
            async with semaphore:
                await execute_copy_signal(item)
        asyncio.create_task(_run(signal))
