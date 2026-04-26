from dataclasses import dataclass
from typing import Any

from .exchanges import validate_strategy_exchange
from .settings import get_settings


@dataclass(frozen=True)
class RiskResult:
    allowed: bool
    reason: str
    normalized_orders: list[dict[str, Any]]


def pre_trade_risk_check(bot: dict[str, Any], orders: list[dict[str, Any]], live_enabled: bool) -> RiskResult:
    settings = get_settings()
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
    global_max = float(settings.global_max_order_notional_usdt)
    if max_position <= 0 or per_tick <= 0:
        return RiskResult(False, 'Risk limits must be positive.', [])
    for order in orders:
        qty = float(order.get('qty', 0))
        price = float(order.get('price') or order.get('reference_price') or order.get('mark_price') or 0) or None
        notional = float(order.get('notional_usdt') or 0)
        if notional <= 0 and price:
            notional = qty * price
        if notional <= 0:
            notional = min(per_tick, max_position)
        if qty <= 0:
            return RiskResult(False, 'Order quantity must be positive.', [])
        if notional > max_position:
            return RiskResult(False, f'Order notional {notional} exceeds bot max_position_usdt {max_position}.', [])
        if notional > global_max:
            return RiskResult(False, f'Order notional {notional} exceeds global max order notional {global_max}.', [])
        side = str(order.get('side') or '').upper()
        if side not in {'BUY', 'SELL'}:
            return RiskResult(False, f'Unsupported side: {side}', [])
        order_type = str(order.get('type') or order.get('order_type') or 'LIMIT').upper()
        if order_type not in {'MARKET', 'LIMIT'}:
            return RiskResult(False, f'Unsupported order type: {order_type}', [])
        normalized.append({**order, 'side': side, 'type': order_type, 'qty': qty, 'notional_usdt': notional, 'reference_price': price})
    return RiskResult(True, 'ok', normalized)
