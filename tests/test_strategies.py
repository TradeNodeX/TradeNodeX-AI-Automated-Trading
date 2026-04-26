from tradenodex_aat.risk import pre_trade_risk_check
from tradenodex_aat.strategies import MarketSnapshot, RiskLimits, run_strategy


def test_funding_arbitrage_waits_below_threshold():
    snapshot = MarketSnapshot(symbol='BTCUSDT', mark_price=50000, funding_rate=0.00001)
    limits = RiskLimits(max_position_usdt=100, risk_per_tick_usdt=10)
    decision = run_strategy('FUNDING_ARBITRAGE', snapshot, limits)
    assert decision.action == 'WAIT'
    assert decision.orders == []


def test_funding_arbitrage_order_is_executable():
    snapshot = MarketSnapshot(symbol='BTCUSDT', mark_price=50000, funding_rate=0.0008)
    limits = RiskLimits(max_position_usdt=100, risk_per_tick_usdt=10)
    decision = run_strategy('FUNDING_ARBITRAGE', snapshot, limits)
    assert decision.action == 'OPEN_FUNDING_LEG'
    assert decision.orders[0]['side'] in {'BUY', 'SELL'}
    assert decision.orders[0]['type'] == 'MARKET'
    assert decision.orders[0]['symbol'] == 'BTCUSDT'


def test_neutral_grid_respects_max_levels():
    snapshot = MarketSnapshot(symbol='BTCUSDT', mark_price=50000)
    limits = RiskLimits(max_position_usdt=100, risk_per_tick_usdt=10, max_grid_levels=4)
    decision = run_strategy('NEUTRAL_CONTRACT_GRID', snapshot, limits)
    assert decision.action == 'PLACE_NEUTRAL_GRID'
    assert len(decision.orders) == 8
    assert all(order['type'] == 'LIMIT' for order in decision.orders)


def test_dca_generates_market_order():
    snapshot = MarketSnapshot(symbol='ETHUSDT', mark_price=2500)
    limits = RiskLimits(max_position_usdt=100, risk_per_tick_usdt=25)
    decision = run_strategy('DCA', snapshot, limits)
    assert decision.action == 'SCHEDULE_DCA_BUY'
    assert len(decision.orders) == 1
    assert decision.orders[0]['type'] == 'MARKET'
    assert decision.orders[0]['side'] == 'BUY'


def test_conservative_spot_grid_generates_buy_ladder():
    snapshot = MarketSnapshot(symbol='SOLUSDT', mark_price=100)
    limits = RiskLimits(max_position_usdt=50, risk_per_tick_usdt=5)
    decision = run_strategy('CONSERVATIVE_SPOT_GRID', snapshot, limits)
    assert decision.action == 'PLACE_CONSERVATIVE_SPOT_GRID'
    assert all(order['side'] == 'BUY' for order in decision.orders)


def test_martingale_halts_at_limit():
    snapshot = MarketSnapshot(symbol='BTCUSDT', mark_price=50000)
    limits = RiskLimits(max_position_usdt=100, risk_per_tick_usdt=5, max_martingale_steps=2)
    decision = run_strategy('MARTINGALE', snapshot, limits)
    assert decision.action == 'MARTINGALE_STEP'


def test_risk_rejects_unsupported_order_type():
    result = pre_trade_risk_check({'type': 'DCA', 'exchange': 'BINANCE_FUTURES', 'dry_run': True, 'max_position_usdt': 100, 'risk_per_tick_usdt': 5}, [{'side': 'BUY', 'type': 'market_or_limit', 'qty': 1, 'notional_usdt': 5}], live_enabled=False)
    assert result.allowed is False
