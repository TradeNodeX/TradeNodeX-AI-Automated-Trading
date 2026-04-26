import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from .db import add_log, connect, utc_now


@dataclass(frozen=True)
class SignalEvent:
    id: str
    source: str
    symbol: str
    side: str
    order_type: str
    notional_usdt: float
    price: float | None = None
    multiplier: float = 1.0
    slippage_bps: float = 20.0
    target_account_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    created_ts: float = field(default_factory=time.time)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> 'SignalEvent':
        return cls(
            id=payload.get('id') or str(uuid4()),
            source=payload.get('source', 'websocket'),
            symbol=str(payload['symbol']).upper(),
            side=str(payload['side']).upper(),
            order_type=str(payload.get('order_type') or payload.get('type') or 'MARKET').upper(),
            notional_usdt=float(payload.get('notional_usdt', 0)),
            price=payload.get('price'),
            multiplier=float(payload.get('multiplier', 1.0)),
            slippage_bps=float(payload.get('slippage_bps', 20.0)),
            target_account_id=payload.get('target_account_id'),
            raw=payload,
        )


class SignalBus:
    def __init__(self, maxsize: int = 5000) -> None:
        self.queue: asyncio.Queue[SignalEvent] = asyncio.Queue(maxsize=maxsize)
        self.clients: set[WebSocket] = set()

    async def publish(self, signal: SignalEvent) -> None:
        await self.queue.put(signal)
        persist_signal(signal, status='QUEUED')
        await self.broadcast({'event': 'signal_queued', 'signal': asdict(signal)})

    async def broadcast(self, message: dict[str, Any]) -> None:
        disconnected = []
        for websocket in self.clients:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.clients.discard(websocket)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)
        await websocket.send_json({'event': 'connected', 'service': 'TradeNodeX signal bus'})

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)


SIGNAL_BUS = SignalBus()


def persist_signal(signal: SignalEvent, status: str) -> None:
    row = asdict(signal)
    with connect() as conn:
        conn.execute('INSERT OR REPLACE INTO signal_events (id,source,symbol,side,order_type,notional_usdt,price,multiplier,slippage_bps,raw_json,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (signal.id, signal.source, signal.symbol, signal.side, signal.order_type, signal.notional_usdt, signal.price, signal.multiplier, signal.slippage_bps, json.dumps(row), status, utc_now()))
    add_log('Signal event persisted', detail={'signal_id': signal.id, 'status': status, 'symbol': signal.symbol, 'side': signal.side})


def persist_execution_event(signal_id: str, status: str, account_id: str | None = None, bot_id: str | None = None, latency_ms: float | None = None, error: str | None = None, detail: dict[str, Any] | None = None) -> None:
    with connect() as conn:
        conn.execute('INSERT INTO execution_events (id,signal_id,account_id,bot_id,status,latency_ms,error,detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)', (str(uuid4()), signal_id, account_id, bot_id, status, latency_ms, error, json.dumps(detail or {}), utc_now()))


def list_recent_signals(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM signal_events ORDER BY created_at DESC LIMIT ?', (limit,))]


def list_recent_execution_events(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM execution_events ORDER BY created_at DESC LIMIT ?', (limit,))]
