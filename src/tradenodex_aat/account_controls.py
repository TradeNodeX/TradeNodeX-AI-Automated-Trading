import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .db import add_log, connect, row_to_dict, utc_now


@dataclass
class TokenBucket:
    capacity: int
    refill_per_second: float
    tokens: float
    updated_at: float = field(default_factory=time.monotonic)

    def allow(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        self.updated_at = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


_BUCKETS: dict[str, TokenBucket] = {}
_FAILURES: dict[str, list[float]] = {}


def init_account_control_schema() -> None:
    with connect() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS account_groups (id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS account_group_members (group_id TEXT NOT NULL,account_id TEXT NOT NULL,multiplier REAL NOT NULL DEFAULT 1.0,is_enabled INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(group_id, account_id));
            CREATE TABLE IF NOT EXISTS account_risk_budgets (account_id TEXT PRIMARY KEY,max_order_notional_usdt REAL NOT NULL,max_daily_notional_usdt REAL NOT NULL,max_position_notional_usdt REAL NOT NULL,min_free_balance_usdt REAL NOT NULL,max_slippage_bps REAL NOT NULL,rate_limit_per_minute INTEGER NOT NULL,failures_before_circuit_break INTEGER NOT NULL,circuit_break_seconds INTEGER NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS account_runtime_metrics (account_id TEXT PRIMARY KEY,realized_pnl_usdt REAL NOT NULL DEFAULT 0,unrealized_pnl_usdt REAL NOT NULL DEFAULT 0,daily_notional_usdt REAL NOT NULL DEFAULT 0,order_count INTEGER NOT NULL DEFAULT 0,last_latency_ms REAL,last_error TEXT,circuit_open_until REAL NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS signal_events (id TEXT PRIMARY KEY,source TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,order_type TEXT NOT NULL,notional_usdt REAL NOT NULL,price REAL,multiplier REAL NOT NULL,slippage_bps REAL NOT NULL,raw_json TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS execution_events (id TEXT PRIMARY KEY,signal_id TEXT NOT NULL,account_id TEXT,bot_id TEXT,status TEXT NOT NULL,latency_ms REAL,error TEXT,detail_json TEXT NOT NULL,created_at TEXT NOT NULL);
        ''')


def create_account_group(name: str, description: str | None = None) -> dict[str, Any]:
    now = utc_now()
    row = {'id': str(uuid4()), 'name': name, 'description': description, 'created_at': now, 'updated_at': now}
    with connect() as conn:
        conn.execute('INSERT INTO account_groups VALUES (:id,:name,:description,:created_at,:updated_at)', row)
    add_log('Account group created', detail={'group_id': row['id'], 'name': name})
    return row


def assign_account_to_group(group_id: str, account_id: str, multiplier: float = 1.0, is_enabled: bool = True) -> dict[str, Any]:
    now = utc_now()
    row = {'group_id': group_id, 'account_id': account_id, 'multiplier': float(multiplier), 'is_enabled': int(is_enabled), 'created_at': now, 'updated_at': now}
    with connect() as conn:
        conn.execute('INSERT INTO account_group_members VALUES (:group_id,:account_id,:multiplier,:is_enabled,:created_at,:updated_at) ON CONFLICT(group_id, account_id) DO UPDATE SET multiplier=:multiplier,is_enabled=:is_enabled,updated_at=:updated_at', row)
    add_log('Account assigned to group', detail={'group_id': group_id, 'account_id': account_id, 'multiplier': multiplier})
    return {**row, 'is_enabled': bool(row['is_enabled'])}


def set_account_risk_budget(account_id: str, budget: dict[str, Any]) -> dict[str, Any]:
    row = {
        'account_id': account_id,
        'max_order_notional_usdt': float(budget.get('max_order_notional_usdt', 50)),
        'max_daily_notional_usdt': float(budget.get('max_daily_notional_usdt', 500)),
        'max_position_notional_usdt': float(budget.get('max_position_notional_usdt', 500)),
        'min_free_balance_usdt': float(budget.get('min_free_balance_usdt', 10)),
        'max_slippage_bps': float(budget.get('max_slippage_bps', 30)),
        'rate_limit_per_minute': int(budget.get('rate_limit_per_minute', 30)),
        'failures_before_circuit_break': int(budget.get('failures_before_circuit_break', 3)),
        'circuit_break_seconds': int(budget.get('circuit_break_seconds', 300)),
        'updated_at': utc_now(),
    }
    with connect() as conn:
        conn.execute('INSERT INTO account_risk_budgets VALUES (:account_id,:max_order_notional_usdt,:max_daily_notional_usdt,:max_position_notional_usdt,:min_free_balance_usdt,:max_slippage_bps,:rate_limit_per_minute,:failures_before_circuit_break,:circuit_break_seconds,:updated_at) ON CONFLICT(account_id) DO UPDATE SET max_order_notional_usdt=:max_order_notional_usdt,max_daily_notional_usdt=:max_daily_notional_usdt,max_position_notional_usdt=:max_position_notional_usdt,min_free_balance_usdt=:min_free_balance_usdt,max_slippage_bps=:max_slippage_bps,rate_limit_per_minute=:rate_limit_per_minute,failures_before_circuit_break=:failures_before_circuit_break,circuit_break_seconds=:circuit_break_seconds,updated_at=:updated_at', row)
    return row


def list_account_groups() -> list[dict[str, Any]]:
    with connect() as conn:
        groups = [row_to_dict(row) for row in conn.execute('SELECT * FROM account_groups ORDER BY created_at DESC')]
        members = [row_to_dict(row) for row in conn.execute('SELECT * FROM account_group_members')]
    by_group: dict[str, list[dict[str, Any]]] = {}
    for item in members:
        item['is_enabled'] = bool(item['is_enabled'])
        by_group.setdefault(item['group_id'], []).append(item)
    for group in groups:
        group['members'] = by_group.get(group['id'], [])
    return groups


def list_account_risk_budgets() -> list[dict[str, Any]]:
    with connect() as conn:
        return [row_to_dict(row) for row in conn.execute('SELECT * FROM account_risk_budgets ORDER BY updated_at DESC')]


def get_account_risk_budget(account_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute('SELECT * FROM account_risk_budgets WHERE account_id=?', (account_id,)).fetchone()
    if row:
        return row_to_dict(row)
    return set_account_risk_budget(account_id, {})


def _bucket_for(account_id: str, rate_limit_per_minute: int) -> TokenBucket:
    bucket = _BUCKETS.get(account_id)
    if not bucket:
        bucket = TokenBucket(capacity=max(rate_limit_per_minute, 1), refill_per_second=max(rate_limit_per_minute, 1) / 60.0, tokens=max(rate_limit_per_minute, 1))
        _BUCKETS[account_id] = bucket
    return bucket


def account_can_execute(account_id: str, notional_usdt: float, slippage_bps: float) -> tuple[bool, str]:
    budget = get_account_risk_budget(account_id)
    with connect() as conn:
        metrics = conn.execute('SELECT * FROM account_runtime_metrics WHERE account_id=?', (account_id,)).fetchone()
    now = time.time()
    if metrics and float(metrics['circuit_open_until'] or 0) > now:
        return False, 'account_circuit_breaker_open'
    if notional_usdt > float(budget['max_order_notional_usdt']):
        return False, 'account_max_order_notional_exceeded'
    if slippage_bps > float(budget['max_slippage_bps']):
        return False, 'account_slippage_budget_exceeded'
    if metrics and float(metrics['daily_notional_usdt'] or 0) + notional_usdt > float(budget['max_daily_notional_usdt']):
        return False, 'account_daily_notional_budget_exceeded'
    if not _bucket_for(account_id, int(budget['rate_limit_per_minute'])).allow():
        return False, 'account_rate_limit_exceeded'
    return True, 'ok'


def record_account_execution(account_id: str, notional_usdt: float, latency_ms: float | None = None, error: str | None = None) -> None:
    now = utc_now()
    with connect() as conn:
        current = conn.execute('SELECT * FROM account_runtime_metrics WHERE account_id=?', (account_id,)).fetchone()
        failures = _FAILURES.setdefault(account_id, [])
        if error:
            failures.append(time.time())
            budget = get_account_risk_budget(account_id)
            if len([ts for ts in failures if time.time() - ts < 300]) >= int(budget['failures_before_circuit_break']):
                circuit_until = time.time() + int(budget['circuit_break_seconds'])
            else:
                circuit_until = float(current['circuit_open_until']) if current else 0
        else:
            failures.clear()
            circuit_until = float(current['circuit_open_until']) if current else 0
        if current:
            conn.execute('UPDATE account_runtime_metrics SET daily_notional_usdt=daily_notional_usdt+?,order_count=order_count+1,last_latency_ms=?,last_error=?,circuit_open_until=?,updated_at=? WHERE account_id=?', (float(notional_usdt), latency_ms, error, circuit_until, now, account_id))
        else:
            conn.execute('INSERT INTO account_runtime_metrics (account_id,daily_notional_usdt,order_count,last_latency_ms,last_error,circuit_open_until,updated_at) VALUES (?,?,?,?,?,?,?)', (account_id, float(notional_usdt), 1, latency_ms, error, circuit_until, now))


def list_account_runtime_metrics() -> list[dict[str, Any]]:
    with connect() as conn:
        return [row_to_dict(row) for row in conn.execute('SELECT * FROM account_runtime_metrics ORDER BY updated_at DESC')]
