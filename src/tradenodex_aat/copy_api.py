from typing import Literal

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .account_controls import list_account_runtime_metrics, list_account_risk_budgets, set_account_risk_budget
from .auth import require_operator_token
from .settings import get_settings
from .signal_bus import SIGNAL_BUS, SignalEvent, list_recent_execution_events, list_recent_signals

router = APIRouter()


class CopySignalIn(BaseModel):
    symbol: str
    side: Literal['BUY', 'SELL']
    order_type: Literal['MARKET', 'LIMIT'] = 'MARKET'
    notional_usdt: float = 5
    price: float | None = None
    multiplier: float = 1.0
    slippage_bps: float = 20
    target_account_id: str | None = None
    source: str = 'http'


class AccountRiskBudgetIn(BaseModel):
    max_order_notional_usdt: float = 50
    max_daily_notional_usdt: float = 500
    max_position_notional_usdt: float = 500
    min_free_balance_usdt: float = 10
    max_slippage_bps: float = 30
    rate_limit_per_minute: int = 30
    failures_before_circuit_break: int = 3
    circuit_break_seconds: int = 300


@router.post('/v1/copy/signals', dependencies=[Depends(require_operator_token)])
async def publish_copy_signal(payload: CopySignalIn):
    signal = SignalEvent.from_payload(payload.model_dump())
    await SIGNAL_BUS.publish(signal)
    return {'queued': True, 'signal_id': signal.id, 'queue_size': SIGNAL_BUS.queue.qsize()}


@router.get('/v1/copy/signals')
def recent_signals():
    return list_recent_signals(100)


@router.get('/v1/copy/executions')
def recent_executions():
    return list_recent_execution_events(100)


@router.get('/v1/copy/metrics')
def copy_metrics():
    return {'queue_size': SIGNAL_BUS.queue.qsize(), 'clients': len(SIGNAL_BUS.clients), 'account_metrics': list_account_runtime_metrics(), 'risk_budgets': list_account_risk_budgets()}


@router.post('/v1/accounts/{account_id}/risk-budget', dependencies=[Depends(require_operator_token)])
def update_account_budget(account_id: str, budget: AccountRiskBudgetIn):
    return set_account_risk_budget(account_id, budget.model_dump())


@router.websocket('/ws/signals')
async def ws_signals(websocket: WebSocket):
    token = websocket.query_params.get('token')
    if token != get_settings().operator_token:
        await websocket.close(code=1008)
        return
    await SIGNAL_BUS.connect(websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            signal = SignalEvent.from_payload({**payload, 'source': 'websocket'})
            await SIGNAL_BUS.publish(signal)
            await websocket.send_json({'event': 'accepted', 'signal_id': signal.id, 'queue_size': SIGNAL_BUS.queue.qsize()})
    except WebSocketDisconnect:
        SIGNAL_BUS.disconnect(websocket)
