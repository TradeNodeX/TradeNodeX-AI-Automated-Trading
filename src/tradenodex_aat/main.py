from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Literal
from uuid import uuid4
from datetime import datetime, timezone

Exchange = Literal['BINANCE_FUTURES','BYBIT_LINEAR','OKX_SWAP','KRAKEN_FUTURES','BITMEX','GATEIO_FUTURES','COINBASE_ADVANCED']
BotType = Literal['FUNDING_ARBITRAGE','NEUTRAL_CONTRACT_GRID','DCA','CONSERVATIVE_SPOT_GRID','MARTINGALE']
BotStatus = Literal['DRAFT','RUNNING','PAUSED','STOPPED']

class Account(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    exchange: Exchange
    environment: Literal['TESTNET','MAINNET']='TESTNET'
    base_currency: str='USDT'
    dry_run: bool=True

class Bot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    type: BotType
    exchange: Exchange
    symbols: list[str]=['BTCUSDT']
    quote_currency: str='USDT'
    status: BotStatus='DRAFT'
    dry_run: bool=True
    max_position_usdt: float=100
    risk_per_tick_usdt: float=5
    grid_levels: int=8
    take_profit_pct: float=0.8
    stop_loss_pct: float=3.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Log(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    level: Literal['INFO','WARN','ERROR']='INFO'
    bot_id: str|None=None
    message: str
    detail: dict={}

app = FastAPI(title='TradeNodeX AI Automated Trading', version='0.1.0')
accounts: list[Account] = [Account(name='Binance Futures Demo', exchange='BINANCE_FUTURES'), Account(name='Bybit Linear Demo', exchange='BYBIT_LINEAR')]
bots: list[Bot] = [
    Bot(name='Funding Spread Sentinel', type='FUNDING_ARBITRAGE', exchange='BINANCE_FUTURES', symbols=['BTCUSDT','ETHUSDT']),
    Bot(name='Neutral Grid BTC', type='NEUTRAL_CONTRACT_GRID', exchange='BYBIT_LINEAR'),
    Bot(name='DCA Core ETH', type='DCA', exchange='OKX_SWAP', symbols=['ETHUSDT']),
    Bot(name='Spot Grid Conservative', type='CONSERVATIVE_SPOT_GRID', exchange='GATEIO_FUTURES'),
    Bot(name='Bounded Martingale Pilot', type='MARTINGALE', exchange='BITMEX')
]
logs: list[Log] = [Log(message='TradeNodeX AAT bootstrapped in dry-run mode.')]

STRATEGY_NOTES = {
 'FUNDING_ARBITRAGE':'Monitor positive/negative funding divergence and open hedged legs only when spread, fees and slippage pass threshold.',
 'NEUTRAL_CONTRACT_GRID':'Maintain market-neutral long/short grid with inventory caps, reduce-only exits and volatility-aware spacing.',
 'DCA':'Schedule fixed quote purchases or derivatives accumulation with max allocation, cooldown and drawdown guard.',
 'CONSERVATIVE_SPOT_GRID':'Low-leverage/no-leverage spot-style grid template with narrow order count and capital preservation bias.',
 'MARTINGALE':'Bounded martingale with hard max steps, hard loss cap, cooldown and live-trading opt-in requirement.'
}

def decision(bot: Bot) -> dict:
    return {'bot': bot.name, 'type': bot.type, 'action': 'DRY_RUN_PLAN', 'symbols': bot.symbols, 'note': STRATEGY_NOTES[bot.type], 'risk_per_tick_usdt': bot.risk_per_tick_usdt, 'max_position_usdt': bot.max_position_usdt}

@app.get('/', response_class=HTMLResponse)
def ui():
    return HTMLResponse(open(__file__.replace('main.py','static/index.html'), encoding='utf-8').read())

@app.get('/v1/health')
def health(): return {'ok': True, 'service': 'tradenodex-aat', 'mode': 'dry-run-first'}
@app.get('/v1/dashboard')
def dashboard():
    running=sum(1 for b in bots if b.status=='RUNNING')
    return {'metrics': {'bots': len(bots), 'running': running, 'accounts': len(accounts), 'audit_logs': len(logs)}, 'bots': bots, 'accounts': accounts, 'logs': logs[-20:]}
@app.get('/v1/accounts')
def list_accounts(): return accounts
@app.post('/v1/accounts')
def create_account(account: Account): accounts.append(account); logs.append(Log(message=f'Account created: {account.name}')); return account
@app.get('/v1/bots')
def list_bots(): return bots
@app.post('/v1/bots')
def create_bot(bot: Bot): bots.append(bot); logs.append(Log(bot_id=bot.id, message=f'Bot created: {bot.name}')); return bot
@app.patch('/v1/bots/{bot_id}')
def update_bot(bot_id: str, patch: dict):
    for i,b in enumerate(bots):
        if b.id==bot_id:
            data=b.model_dump(); data.update(patch); bots[i]=Bot(**data); logs.append(Log(bot_id=bot_id,message='Bot updated', detail=patch)); return bots[i]
    return {'error':'not_found'}
@app.post('/v1/bots/{bot_id}/start')
def start(bot_id: str): return set_status(bot_id,'RUNNING')
@app.post('/v1/bots/{bot_id}/pause')
def pause(bot_id: str): return set_status(bot_id,'PAUSED')
@app.post('/v1/bots/{bot_id}/stop')
def stop(bot_id: str): return set_status(bot_id,'STOPPED')
def set_status(bot_id: str, status: BotStatus):
    for b in bots:
        if b.id==bot_id:
            b.status=status; logs.append(Log(bot_id=bot_id,message=f'Bot status changed to {status}')); return b
    return {'error':'not_found'}
@app.post('/v1/bots/{bot_id}/tick')
def tick(bot_id: str):
    for b in bots:
        if b.id==bot_id:
            d=decision(b); logs.append(Log(bot_id=bot_id,message='Strategy tick completed', detail=d)); return d
    return {'error':'not_found'}
@app.get('/v1/logs')
def list_logs(): return logs[-100:]
