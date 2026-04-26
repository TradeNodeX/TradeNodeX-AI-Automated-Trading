from dataclasses import dataclass
from enum import StrEnum

class BotType(StrEnum):
    FUNDING_ARBITRAGE = 'FUNDING_ARBITRAGE'
    NEUTRAL_CONTRACT_GRID = 'NEUTRAL_CONTRACT_GRID'
    DCA = 'DCA'
    CONSERVATIVE_SPOT_GRID = 'CONSERVATIVE_SPOT_GRID'
    MARTINGALE = 'MARTINGALE'

@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    mark_price: float
    funding_rate: float = 0.0
    volatility_pct: float = 1.0
    bid: float | None = None
    ask: float | None = None

@dataclass(frozen=True)
class RiskLimits:
    max_position_usdt: float
    risk_per_tick_usdt: float
    max_grid_levels: int = 20
    max_martingale_steps: int = 5
    live_enabled: bool = False

@dataclass(frozen=True)
class StrategyDecision:
    action: str
    symbol: str
    reason: str
    orders: list[dict]
    risk: dict

def _notional_qty(usdt: float, price: float) -> float:
    if price <= 0:
        raise ValueError('mark_price must be positive')
    return round(usdt / price, 8)

def funding_arbitrage(snapshot: MarketSnapshot, limits: RiskLimits, threshold: float = 0.0003) -> StrategyDecision:
    if abs(snapshot.funding_rate) < threshold:
        return StrategyDecision('WAIT', snapshot.symbol, 'Funding rate below threshold after fees/slippage buffer.', [], limits.__dict__)
    side = 'SHORT_PERP_LONG_HEDGE' if snapshot.funding_rate > 0 else 'LONG_PERP_SHORT_HEDGE'
    qty = _notional_qty(min(limits.risk_per_tick_usdt, limits.max_position_usdt), snapshot.mark_price)
    return StrategyDecision('OPEN_HEDGED_LEGS', snapshot.symbol, side, [{'type':'market','leg':'perp','qty':qty},{'type':'hedge','leg':'offset','qty':qty}], limits.__dict__)

def neutral_contract_grid(snapshot: MarketSnapshot, limits: RiskLimits, levels: int = 8, spacing_pct: float = 0.35) -> StrategyDecision:
    levels = max(2, min(levels, limits.max_grid_levels))
    per_order = min(limits.max_position_usdt / levels, limits.risk_per_tick_usdt)
    orders=[]
    for i in range(1, levels + 1):
        buy_price = round(snapshot.mark_price * (1 - spacing_pct/100*i), 4)
        sell_price = round(snapshot.mark_price * (1 + spacing_pct/100*i), 4)
        qty = _notional_qty(per_order, snapshot.mark_price)
        orders.extend([{'side':'BUY','price':buy_price,'qty':qty,'post_only':True},{'side':'SELL','price':sell_price,'qty':qty,'post_only':True}])
    return StrategyDecision('PLACE_NEUTRAL_GRID', snapshot.symbol, 'Symmetric futures grid with inventory cap.', orders, limits.__dict__)

def dca(snapshot: MarketSnapshot, limits: RiskLimits) -> StrategyDecision:
    qty = _notional_qty(min(limits.risk_per_tick_usdt, limits.max_position_usdt), snapshot.mark_price)
    return StrategyDecision('SCHEDULE_DCA_BUY', snapshot.symbol, 'Average-cost tick within allocation budget.', [{'side':'BUY','type':'market_or_limit','qty':qty}], limits.__dict__)

def conservative_spot_grid(snapshot: MarketSnapshot, limits: RiskLimits, levels: int = 5, spacing_pct: float = 0.6) -> StrategyDecision:
    levels = max(2, min(levels, 10))
    per_order = min(limits.max_position_usdt / levels, limits.risk_per_tick_usdt)
    orders=[]
    for i in range(1, levels + 1):
        price = round(snapshot.mark_price * (1 - spacing_pct/100*i), 4)
        orders.append({'side':'BUY','price':price,'qty':_notional_qty(per_order, snapshot.mark_price),'post_only':True})
    return StrategyDecision('PLACE_CONSERVATIVE_SPOT_GRID', snapshot.symbol, 'Capital-preservation grid; sell legs are generated after inventory exists.', orders, limits.__dict__)

def martingale(snapshot: MarketSnapshot, limits: RiskLimits, step: int = 0, base_usdt: float | None = None) -> StrategyDecision:
    if step >= limits.max_martingale_steps:
        return StrategyDecision('HALT', snapshot.symbol, 'Max martingale step reached.', [], limits.__dict__)
    base = base_usdt or limits.risk_per_tick_usdt
    notional = min(base * (2 ** step), limits.max_position_usdt)
    qty = _notional_qty(notional, snapshot.mark_price)
    return StrategyDecision('MARTINGALE_STEP', snapshot.symbol, f'Bounded martingale step {step}.', [{'side':'BUY','qty':qty,'notional_usdt':notional}], limits.__dict__)

def run_strategy(bot_type: str, snapshot: MarketSnapshot, limits: RiskLimits) -> StrategyDecision:
    if bot_type == BotType.FUNDING_ARBITRAGE: return funding_arbitrage(snapshot, limits)
    if bot_type == BotType.NEUTRAL_CONTRACT_GRID: return neutral_contract_grid(snapshot, limits)
    if bot_type == BotType.DCA: return dca(snapshot, limits)
    if bot_type == BotType.CONSERVATIVE_SPOT_GRID: return conservative_spot_grid(snapshot, limits)
    if bot_type == BotType.MARTINGALE: return martingale(snapshot, limits)
    raise ValueError(f'Unsupported bot type: {bot_type}')
