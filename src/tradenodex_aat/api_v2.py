from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .db import add_log, create_account, create_bot, get_bot, init_db, list_accounts, list_bots, list_logs, list_orders, list_positions, update_bot
from .executor import execute_strategy_orders
from .market_stream import poll_market_snapshot
from .reconciliation import reconcile_all_accounts
from .settings import get_settings
from .strategies import MarketSnapshot, RiskLimits, run_strategy
from .validation import validation_plan

Exchange = Literal['BINANCE_FUTURES','BYBIT_LINEAR','OKX_SWAP','KRAKEN_FUTURES','BITMEX','GATEIO_FUTURES','COINBASE_ADVANCED']
BotType = Literal['FUNDING_ARBITRAGE','NEUTRAL_CONTRACT_GRID','DCA','CONSERVATIVE_SPOT_GRID','MARTINGALE']
BotStatus = Literal['DRAFT','RUNNING','PAUSED','STOPPED']

class AccountIn(BaseModel):
    name: str
    exchange: Exchange
    environment: Literal['TESTNET','MAINNET'] = 'TESTNET'
    base_currency: str = 'USDT'
    dry_run: bool = True
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None

class BotIn(BaseModel):
    name: str
    type: BotType
    exchange: Exchange
    symbols: list[str] = Field(default_factory=lambda: ['BTCUSDT'])
    quote_currency: str = 'USDT'
    status: BotStatus = 'DRAFT'
    dry_run: bool = True
    max_position_usdt: float = 100
    risk_per_tick_usdt: float = 5
    grid_levels: int = 8
    take_profit_pct: float = 0.8
    stop_loss_pct: float = 3.0
    account_id: str | None = None

class MarketSnapshotIn(BaseModel):
    exchange: Exchange
    symbol: str

app = FastAPI(title='TradeNodeX AI Automated Trading', version='0.2.0')

@app.on_event('startup')
def startup() -> None:
    init_db()

@app.get('/', response_class=HTMLResponse)
def ui():
    index = Path(__file__).with_name('static').joinpath('index.html')
    return HTMLResponse(index.read_text(encoding='utf-8'))

@app.get('/v1/health')
def health():
    settings = get_settings()
    return {'ok': True, 'service': 'tradenodex-aat', 'version': '0.2.0', 'live_trading_enabled': settings.enable_live_trading}

@app.get('/v1/dashboard')
def dashboard():
    bots = list_bots(); accounts = list_accounts(); logs = list_logs(20); orders = list_orders(20); positions = list_positions()
    running = sum(1 for b in bots if b['status'] == 'RUNNING')
    return {'metrics': {'bots': len(bots), 'running': running, 'accounts': len(accounts), 'audit_logs': len(logs), 'orders': len(orders), 'positions': len(positions)}, 'bots': bots, 'accounts': accounts, 'logs': logs, 'orders': orders, 'positions': positions}

@app.get('/v1/accounts')
def api_list_accounts(): return list_accounts()

@app.post('/v1/accounts')
def api_create_account(account: AccountIn): return create_account(account.model_dump())

@app.get('/v1/bots')
def api_list_bots(): return list_bots()

@app.post('/v1/bots')
def api_create_bot(bot: BotIn): return create_bot(bot.model_dump())

@app.patch('/v1/bots/{bot_id}')
def api_update_bot(bot_id: str, patch: dict):
    updated = update_bot(bot_id, patch)
    if not updated: raise HTTPException(status_code=404, detail='bot_not_found')
    return updated

@app.post('/v1/bots/{bot_id}/start')
def start(bot_id: str): return _set_status(bot_id, 'RUNNING')
@app.post('/v1/bots/{bot_id}/pause')
def pause(bot_id: str): return _set_status(bot_id, 'PAUSED')
@app.post('/v1/bots/{bot_id}/stop')
def stop(bot_id: str): return _set_status(bot_id, 'STOPPED')

def _set_status(bot_id: str, status: str):
    updated = update_bot(bot_id, {'status': status})
    if not updated: raise HTTPException(status_code=404, detail='bot_not_found')
    return updated

@app.post('/v1/bots/{bot_id}/tick')
async def tick(bot_id: str):
    bot = get_bot(bot_id)
    if not bot: raise HTTPException(status_code=404, detail='bot_not_found')
    symbol = bot['symbols'][0]
    funding = 0.0004 if bot['type'] == 'FUNDING_ARBITRAGE' else 0.0
    snapshot = MarketSnapshot(symbol=symbol, mark_price=50000.0, funding_rate=funding)
    limits = RiskLimits(max_position_usdt=bot['max_position_usdt'], risk_per_tick_usdt=bot['risk_per_tick_usdt'], max_grid_levels=bot['grid_levels'])
    decision = asdict(run_strategy(bot['type'], snapshot, limits)); decision['bot'] = bot['name']
    execution = await execute_strategy_orders(bot, decision)
    add_log('Strategy tick completed', bot_id=bot_id, detail={'decision': decision, 'execution': execution})
    return {'decision': decision, 'execution': execution}

@app.get('/v1/orders')
def api_list_orders(): return list_orders(100)
@app.get('/v1/positions')
def api_list_positions(): return list_positions()
@app.post('/v1/reconcile')
async def api_reconcile(): return await reconcile_all_accounts()
@app.post('/v1/market-snapshot')
async def api_market_snapshot(payload: MarketSnapshotIn): return await poll_market_snapshot(payload.exchange, payload.symbol)
@app.get('/v1/validation-plan')
def api_validation_plan(): return validation_plan()
@app.get('/v1/logs')
def api_list_logs(): return list_logs(100)
