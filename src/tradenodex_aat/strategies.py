from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


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
class PositionContext:
    symbol: str
    qty: float = 0.0
    side: str = 'NET'
    entry_price: float | None = None


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
    orders: list[dict[str, Any]]
    risk: dict[str, Any]
    state_patch: dict[str, Any]


def _notional_qty(usdt: float, price: float) -> float:
    if price <= 0:
        raise ValueError('mark_price must be positive')
    return round(usdt / price, 8)


def _risk_dict(limits: RiskLimits) -> dict[str, Any]:
    return asdict(limits)


def funding_arbitrage(snapshot: MarketSnapshot, limits: RiskLimits, threshold: float = 0.0003) -> StrategyDecision:
    fee_slippage_buffer = 0.0001
    effective_threshold = threshold + fee_slippage_buffer
    if abs(snapshot.funding_rate) < effective_threshold:
        return StrategyDecision('WAIT', snapshot.symbol, 'Funding rate below net threshold after fee/slippage buffer.', [], _risk_dict(limits), {})
    notional = min(limits.risk_per_tick_usdt, limits.max_position_usdt)
    qty = _notional_qty(notional, snapshot.mark_price)
    if snapshot.funding_rate > 0:
        orders = [{'leg':'perp','side':'SELL','type':'MARKET','symbol':snapshot.symbol,'qty':qty,'notional_usdt':notional,'reduce_only':False}]
        reason = 'Positive funding: short perpetual leg. External hedge leg must be configured before production hedge deployment.'
    else:
        orders = [{'leg':'perp','side':'BUY','type':'MARKET','symbol':snapshot.symbol,'qty':qty,'notional_usdt':notional,'reduce_only':False}]
        reason = 'Negative funding: long perpetual leg. External hedge leg must be configured before production hedge deployment.'
    return StrategyDecision('OPEN_FUNDING_LEG', snapshot.symbol, reason, orders, _risk_dict(limits), {'last_funding_rate': snapshot.funding_rate})


def neutral_contract_grid(snapshot: MarketSnapshot, limits: RiskLimits, levels: int = 8, spacing_pct: float = 0.35) -> StrategyDecision:
    levels = max(2, min(levels, limits.max_grid_levels))
    per_order = min(limits.max_position_usdt / levels, limits.risk_per_tick_usdt)
    orders = []
    for i in range(1, levels + 1):
        buy_price = round(snapshot.mark_price * (1 - spacing_pct / 100 * i), 4)
        sell_price = round(snapshot.mark_price * (1 + spacing_pct / 100 * i), 4)
        qty = _notional_qty(per_order, snapshot.mark_price)
        orders.extend([
            {'side':'BUY','type':'LIMIT','symbol':snapshot.symbol,'price':buy_price,'qty':qty,'notional_usdt':per_order,'post_only':True},
            {'side':'SELL','type':'LIMIT','symbol':snapshot.symbol,'price':sell_price,'qty':qty,'notional_usdt':per_order,'post_only':True},
        ])
    return StrategyDecision('PLACE_NEUTRAL_GRID', snapshot.symbol, 'Symmetric futures grid with inventory cap and post-only orders.', orders, _risk_dict(limits), {'grid_levels': levels})


def dca(snapshot: MarketSnapshot, limits: RiskLimits) -> StrategyDecision:
    notional = min(limits.risk_per_tick_usdt, limits.max_position_usdt)
    qty = _notional_qty(notional, snapshot.mark_price)
    return StrategyDecision('SCHEDULE_DCA_BUY', snapshot.symbol, 'Average-cost market tick within allocation budget.', [{'side':'BUY','type':'MARKET','symbol':snapshot.symbol,'qty':qty,'notional_usdt':notional}], _risk_dict(limits), {'last_dca_price': snapshot.mark_price})


def conservative_spot_grid(snapshot: MarketSnapshot, limits: RiskLimits, levels: int = 5, spacing_pct: float = 0.6) -> StrategyDecision:
    levels = max(2, min(levels, 10))
    per_order = min(limits.max_position_usdt / levels, limits.risk_per_tick_usdt)
    orders = []
    for i in range(1, levels + 1):
        price = round(snapshot.mark_price * (1 - spacing_pct / 100 * i), 4)
        orders.append({'side':'BUY','type':'LIMIT','symbol':snapshot.symbol,'price':price,'qty':_notional_qty(per_order, snapshot.mark_price),'notional_usdt':per_order,'post_only':True})
    return StrategyDecision('PLACE_CONSERVATIVE_SPOT_GRID', snapshot.symbol, 'Capital-preservation grid; sell legs are created only after confirmed inventory.', orders, _risk_dict(limits), {'grid_levels': levels})


def martingale(snapshot: MarketSnapshot, limits: RiskLimits, step: int = 0, base_usdt: float | None = None) -> StrategyDecision:
    if step >= limits.max_martingale_steps:
        return StrategyDecision('HALT', snapshot.symbol, 'Max martingale step reached.', [], _risk_dict(limits), {'halt_reason': 'max_step'})
    base = base_usdt or limits.risk_per_tick_usdt
    notional = min(base * (2 ** step), limits.max_position_usdt)
    qty = _notional_qty(notional, snapshot.mark_price)
    return StrategyDecision('MARTINGALE_STEP', snapshot.symbol, f'Bounded martingale step {step}.', [{'side':'BUY','type':'MARKET','symbol':snapshot.symbol,'qty':qty,'notional_usdt':notional}], _risk_dict(limits), {'next_step': step + 1})


def run_strategy(bot_type: str, snapshot: MarketSnapshot, limits: RiskLimits, state: dict[str, Any] | None = None) -> StrategyDecision:
    state = state or {}
    if bot_type == BotType.FUNDING_ARBITRAGE: return funding_arbitrage(snapshot, limits)
    if bot_type == BotType.NEUTRAL_CONTRACT_GRID: return neutral_contract_grid(snapshot, limits, levels=limits.max_grid_levels)
    if bot_type == BotType.DCA: return dca(snapshot, limits)
    if bot_type == BotType.CONSERVATIVE_SPOT_GRID: return conservative_spot_grid(snapshot, limits)
    if bot_type == BotType.MARTINGALE: return martingale(snapshot, limits, step=int(state.get('step', 0)))
    raise ValueError(f'Unsupported bot type: {bot_type}')
