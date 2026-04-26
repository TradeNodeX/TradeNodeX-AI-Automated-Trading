import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .crypto import encrypt_secret, mask_secret
from .settings import get_settings

SCHEMA_VERSION = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    Path(settings.db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('schema_version', '2');
            CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY,name TEXT NOT NULL,exchange TEXT NOT NULL,environment TEXT NOT NULL,base_currency TEXT NOT NULL,dry_run INTEGER NOT NULL,api_key_encrypted TEXT,api_secret_encrypted TEXT,api_passphrase_encrypted TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS bots (id TEXT PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,exchange TEXT NOT NULL,symbols_json TEXT NOT NULL,quote_currency TEXT NOT NULL,status TEXT NOT NULL,dry_run INTEGER NOT NULL,max_position_usdt REAL NOT NULL,risk_per_tick_usdt REAL NOT NULL,grid_levels INTEGER NOT NULL,take_profit_pct REAL NOT NULL,stop_loss_pct REAL NOT NULL,account_id TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit_logs (id TEXT PRIMARY KEY,ts TEXT NOT NULL,level TEXT NOT NULL,bot_id TEXT,message TEXT NOT NULL,detail_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY,bot_id TEXT NOT NULL,idempotency_key TEXT NOT NULL UNIQUE,exchange TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,order_type TEXT NOT NULL,qty REAL NOT NULL,price REAL,status TEXT NOT NULL,attempts INTEGER NOT NULL,last_error TEXT,raw_response_json TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS positions (id TEXT PRIMARY KEY,account_id TEXT,exchange TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,qty REAL NOT NULL,entry_price REAL,mark_price REAL,unrealized_pnl REAL,updated_at TEXT NOT NULL,UNIQUE(exchange, symbol, side, account_id));
            CREATE TABLE IF NOT EXISTS balances (id TEXT PRIMARY KEY,account_id TEXT,exchange TEXT NOT NULL,asset TEXT NOT NULL,free REAL,total REAL,used REAL,updated_at TEXT NOT NULL,UNIQUE(exchange, asset, account_id));
            CREATE TABLE IF NOT EXISTS open_orders (id TEXT PRIMARY KEY,account_id TEXT,exchange TEXT NOT NULL,symbol TEXT NOT NULL,client_order_id TEXT,side TEXT,qty REAL,price REAL,status TEXT,raw_json TEXT,updated_at TEXT NOT NULL,UNIQUE(exchange, symbol, client_order_id, account_id));
            CREATE TABLE IF NOT EXISTS market_snapshots (id TEXT PRIMARY KEY,exchange TEXT NOT NULL,symbol TEXT NOT NULL,mark_price REAL NOT NULL,funding_rate REAL NOT NULL,bid REAL,ask REAL,source TEXT NOT NULL,ts TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_ts ON audit_logs(ts);
            CREATE INDEX IF NOT EXISTS idx_orders_bot_status ON orders(bot_id, status);
            CREATE INDEX IF NOT EXISTS idx_market_snapshots_symbol_ts ON market_snapshots(exchange, symbol, ts);
        ''')
    seed_demo_data()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def add_log(message: str, level: str = 'INFO', bot_id: str | None = None, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {'id': str(uuid4()), 'ts': utc_now(), 'level': level, 'bot_id': bot_id, 'message': message, 'detail_json': json.dumps(detail or {})}
    with connect() as conn:
        conn.execute('INSERT INTO audit_logs VALUES (:id,:ts,:level,:bot_id,:message,:detail_json)', payload)
    return {**payload, 'detail': detail or {}}


def create_account(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    payload = {'id': data.get('id') or str(uuid4()), 'name': data['name'], 'exchange': data['exchange'], 'environment': data.get('environment', 'TESTNET'), 'base_currency': data.get('base_currency', 'USDT'), 'dry_run': int(data.get('dry_run', True)), 'api_key_encrypted': encrypt_secret(data.get('api_key')), 'api_secret_encrypted': encrypt_secret(data.get('api_secret')), 'api_passphrase_encrypted': encrypt_secret(data.get('api_passphrase')), 'created_at': now, 'updated_at': now}
    with connect() as conn:
        conn.execute('INSERT INTO accounts VALUES (:id,:name,:exchange,:environment,:base_currency,:dry_run,:api_key_encrypted,:api_secret_encrypted,:api_passphrase_encrypted,:created_at,:updated_at)', payload)
    add_log(f"Account created: {payload['name']}", detail={'exchange': payload['exchange'], 'environment': payload['environment']})
    return public_account(payload)


def public_account(row: dict[str, Any] | sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row) if isinstance(row, sqlite3.Row) else dict(row)
    return {'id': item['id'], 'name': item['name'], 'exchange': item['exchange'], 'environment': item['environment'], 'base_currency': item['base_currency'], 'dry_run': bool(item['dry_run']), 'api_key_masked': mask_secret(item.get('api_key_encrypted')), 'has_secret': bool(item.get('api_secret_encrypted')), 'created_at': item['created_at'], 'updated_at': item['updated_at']}


def list_accounts() -> list[dict[str, Any]]:
    with connect() as conn:
        return [public_account(row) for row in conn.execute('SELECT * FROM accounts ORDER BY created_at DESC')]


def create_bot(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    payload = {'id': data.get('id') or str(uuid4()), 'name': data['name'], 'type': data['type'], 'exchange': data['exchange'], 'symbols_json': json.dumps(data.get('symbols') or ['BTCUSDT']), 'quote_currency': data.get('quote_currency', 'USDT'), 'status': data.get('status', 'DRAFT'), 'dry_run': int(data.get('dry_run', True)), 'max_position_usdt': float(data.get('max_position_usdt', 100)), 'risk_per_tick_usdt': float(data.get('risk_per_tick_usdt', 5)), 'grid_levels': int(data.get('grid_levels', 8)), 'take_profit_pct': float(data.get('take_profit_pct', 0.8)), 'stop_loss_pct': float(data.get('stop_loss_pct', 3.0)), 'account_id': data.get('account_id'), 'created_at': now, 'updated_at': now}
    with connect() as conn:
        conn.execute('INSERT INTO bots VALUES (:id,:name,:type,:exchange,:symbols_json,:quote_currency,:status,:dry_run,:max_position_usdt,:risk_per_tick_usdt,:grid_levels,:take_profit_pct,:stop_loss_pct,:account_id,:created_at,:updated_at)', payload)
    add_log(f"Bot created: {payload['name']}", bot_id=payload['id'], detail={'type': payload['type']})
    return public_bot(payload)


def public_bot(row: dict[str, Any] | sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row) if isinstance(row, sqlite3.Row) else dict(row)
    item['symbols'] = json.loads(item.pop('symbols_json'))
    item['dry_run'] = bool(item['dry_run'])
    return item


def list_bots() -> list[dict[str, Any]]:
    with connect() as conn:
        return [public_bot(row) for row in conn.execute('SELECT * FROM bots ORDER BY created_at DESC')]


def get_bot(bot_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute('SELECT * FROM bots WHERE id=?', (bot_id,)).fetchone()
        return public_bot(row) if row else None


def update_bot(bot_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    current = get_bot(bot_id)
    if not current:
        return None
    current.update(patch)
    current['symbols_json'] = json.dumps(current.pop('symbols'))
    current['dry_run'] = int(current['dry_run'])
    current['updated_at'] = utc_now()
    with connect() as conn:
        conn.execute('''UPDATE bots SET name=:name,type=:type,exchange=:exchange,symbols_json=:symbols_json,quote_currency=:quote_currency,status=:status,dry_run=:dry_run,max_position_usdt=:max_position_usdt,risk_per_tick_usdt=:risk_per_tick_usdt,grid_levels=:grid_levels,take_profit_pct=:take_profit_pct,stop_loss_pct=:stop_loss_pct,account_id=:account_id,updated_at=:updated_at WHERE id=:id''', current)
    add_log('Bot updated', bot_id=bot_id, detail=patch)
    return get_bot(bot_id)


def list_logs(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute('SELECT * FROM audit_logs ORDER BY ts DESC LIMIT ?', (limit,)).fetchall()
    out = []
    for row in rows:
        item = row_to_dict(row); item['detail'] = json.loads(item.pop('detail_json')); out.append(item)
    return out


def insert_order(order: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    payload = {'id': order.get('id') or str(uuid4()), 'bot_id': order['bot_id'], 'idempotency_key': order['idempotency_key'], 'exchange': order['exchange'], 'symbol': order['symbol'], 'side': order['side'], 'order_type': order.get('order_type', 'LIMIT'), 'qty': float(order['qty']), 'price': order.get('price'), 'status': order.get('status', 'PENDING'), 'attempts': int(order.get('attempts', 0)), 'last_error': order.get('last_error'), 'raw_response_json': json.dumps(order.get('raw_response')) if order.get('raw_response') else None, 'created_at': now, 'updated_at': now}
    with connect() as conn:
        conn.execute('INSERT OR IGNORE INTO orders VALUES (:id,:bot_id,:idempotency_key,:exchange,:symbol,:side,:order_type,:qty,:price,:status,:attempts,:last_error,:raw_response_json,:created_at,:updated_at)', payload)
        row = conn.execute('SELECT * FROM orders WHERE idempotency_key=?', (payload['idempotency_key'],)).fetchone()
    return row_to_dict(row)


def update_order(order_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    patch = dict(patch); patch['updated_at'] = utc_now(); assignments = ','.join(f'{k}=?' for k in patch); values = list(patch.values()) + [order_id]
    with connect() as conn:
        conn.execute(f'UPDATE orders SET {assignments} WHERE id=?', values)
        row = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_orders(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        return [row_to_dict(row) for row in conn.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT ?', (limit,))]


def upsert_position(data: dict[str, Any]) -> dict[str, Any]:
    payload = {'id': data.get('id') or str(uuid4()), 'account_id': data.get('account_id'), 'exchange': data['exchange'], 'symbol': data['symbol'], 'side': data.get('side', 'NET'), 'qty': float(data.get('qty', 0)), 'entry_price': data.get('entry_price'), 'mark_price': data.get('mark_price'), 'unrealized_pnl': data.get('unrealized_pnl'), 'updated_at': utc_now()}
    with connect() as conn:
        conn.execute('INSERT INTO positions VALUES (:id,:account_id,:exchange,:symbol,:side,:qty,:entry_price,:mark_price,:unrealized_pnl,:updated_at) ON CONFLICT(exchange,symbol,side,account_id) DO UPDATE SET qty=:qty,entry_price=:entry_price,mark_price=:mark_price,unrealized_pnl=:unrealized_pnl,updated_at=:updated_at', payload)
    return payload


def list_positions() -> list[dict[str, Any]]:
    with connect() as conn:
        return [row_to_dict(row) for row in conn.execute('SELECT * FROM positions ORDER BY updated_at DESC')]


def upsert_balance(data: dict[str, Any]) -> dict[str, Any]:
    payload = {'id': data.get('id') or str(uuid4()), 'account_id': data.get('account_id'), 'exchange': data['exchange'], 'asset': data['asset'], 'free': data.get('free'), 'total': data.get('total'), 'used': data.get('used'), 'updated_at': utc_now()}
    with connect() as conn:
        conn.execute('INSERT INTO balances VALUES (:id,:account_id,:exchange,:asset,:free,:total,:used,:updated_at) ON CONFLICT(exchange,asset,account_id) DO UPDATE SET free=:free,total=:total,used=:used,updated_at=:updated_at', payload)
    return payload


def upsert_open_order(data: dict[str, Any]) -> dict[str, Any]:
    payload = {'id': data.get('id') or str(uuid4()), 'account_id': data.get('account_id'), 'exchange': data['exchange'], 'symbol': data['symbol'], 'client_order_id': data.get('client_order_id'), 'side': data.get('side'), 'qty': data.get('qty'), 'price': data.get('price'), 'status': data.get('status'), 'raw_json': json.dumps(data.get('raw') or {}), 'updated_at': utc_now()}
    with connect() as conn:
        conn.execute('INSERT INTO open_orders VALUES (:id,:account_id,:exchange,:symbol,:client_order_id,:side,:qty,:price,:status,:raw_json,:updated_at) ON CONFLICT(exchange,symbol,client_order_id,account_id) DO UPDATE SET side=:side,qty=:qty,price=:price,status=:status,raw_json=:raw_json,updated_at=:updated_at', payload)
    return payload


def store_market_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    payload = {'id': str(uuid4()), 'exchange': data['exchange'], 'symbol': data['symbol'], 'mark_price': float(data['mark_price']), 'funding_rate': float(data.get('funding_rate', 0)), 'bid': data.get('bid'), 'ask': data.get('ask'), 'source': data.get('source', 'manual'), 'ts': utc_now()}
    with connect() as conn:
        conn.execute('INSERT INTO market_snapshots VALUES (:id,:exchange,:symbol,:mark_price,:funding_rate,:bid,:ask,:source,:ts)', payload)
    return payload


def seed_demo_data() -> None:
    with connect() as conn:
        bot_count = conn.execute('SELECT COUNT(*) AS c FROM bots').fetchone()['c']
        account_count = conn.execute('SELECT COUNT(*) AS c FROM accounts').fetchone()['c']
    if account_count == 0:
        create_account({'name': 'Binance Futures Demo', 'exchange': 'BINANCE_FUTURES', 'environment': 'TESTNET', 'dry_run': True})
        create_account({'name': 'Bybit Linear Demo', 'exchange': 'BYBIT_LINEAR', 'environment': 'TESTNET', 'dry_run': True})
    if bot_count == 0:
        create_bot({'name': 'Funding Spread Sentinel', 'type': 'FUNDING_ARBITRAGE', 'exchange': 'BINANCE_FUTURES', 'symbols': ['BTCUSDT', 'ETHUSDT']})
        create_bot({'name': 'Neutral Grid BTC', 'type': 'NEUTRAL_CONTRACT_GRID', 'exchange': 'BYBIT_LINEAR', 'symbols': ['BTCUSDT']})
        create_bot({'name': 'DCA Core ETH', 'type': 'DCA', 'exchange': 'OKX_SWAP', 'symbols': ['ETHUSDT']})
        create_bot({'name': 'Spot Grid Conservative', 'type': 'CONSERVATIVE_SPOT_GRID', 'exchange': 'GATEIO_FUTURES', 'symbols': ['BTCUSDT']})
        create_bot({'name': 'Bounded Martingale Pilot', 'type': 'MARTINGALE', 'exchange': 'BITMEX', 'symbols': ['BTCUSDT']})
        add_log('TradeNodeX AAT persistent database initialized in dry-run mode.')
