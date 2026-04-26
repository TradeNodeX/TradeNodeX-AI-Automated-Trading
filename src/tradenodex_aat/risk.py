from dataclasses import dataclass
from typing import Any

from .exchanges import validate_strategy_exchange


@dataclass(frozen=True)
class RiskResult:
    allowed: bool
    reason: str
    normalized_orders: list[dict[str, Any]]


def pre_trade_risk_check(bot: dict[str, Any], orders: list[dict[str, Any]], live_enabled: bool) -> RiskResult:
    ok, reason = validate_strategy_exchange(bot['type'], bot['exchange'])
    if not ok:
        return RiskResult(False, reason, [])
    if not bot.get('dry_run', True) and not live_enabled:
        return RiskResult(False, 'Live trading is globally disabled. Set TRADENODEX_AAT_ENABLE_LIVE_TRADING=true only after validation.', [])
    if bot.get('type') == 'MARTINGALE' and float(bot.get('max_position_usdt', 0)) > 500:
        return RiskResult(False, 'Martingale v1 hard cap exceeded: max_position_usdt must be <= 500 unless risk module is extended.', [])
    normalized = []
    max_position = float(bot.get('max_position_usdt', 0))
    per_tick = float(bot.get('risk_per_tick_usdt', 0))
    for order in orders:
        qty = float(order.get('qty', 0))
        price = float(order.get('price') or 0) or None
        notional = float(order.get('notional_usdt') or 0)
        if notional <= 0 and price:
            notional = qty * price
        if notional <= 0:
            notional = min(per_tick, max_position)
        if qty <= 0:
            return RiskResult(False, 'Order quantity must be positive.', [])
        if notional > max_position:
            return RiskResult(False, f'Order notional {notional} exceeds bot max_position_usdt {max_position}.', [])
        side = str(order.get('side') or 'BUY').upper()
        if side not in {'BUY', 'SELL'}:
            return RiskResult(False, f'Unsupported side: {side}', [])
        normalized.append({**order, 'side': side, 'qty': qty, 'notional_usdt': notional})
    return RiskResult(True, 'ok', normalized)
