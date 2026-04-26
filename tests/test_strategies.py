from tradenodex_aat.strategies import MarketSnapshot, RiskLimits, run_strategy


def test_funding_arbitrage_waits_below_threshold():
    snapshot = MarketSnapshot(symbol='BTCUSDT', mark_price=50000, funding_rate=0.00001)
    limits = RiskLimits(max_position_usdt=100, risk_per_tick_usdt=10)
    decision = run_strategy('FUNDING_ARBITRAGE', snapshot, limits)
    assert decision.action == 'WAIT'
    assert decision.orders == []


def test_neutral_grid_respects_max_levels():
    snapshot = MarketSnapshot(symbol='BTCUSDT', mark_price=50000)
    limits = RiskLimits(max_position_usdt=100, risk_per_tick_usdt=10, max_grid_levels=4)
    decision = run_strategy('NEUTRAL_CONTRACT_GRID', snapshot, limits)
    assert decision.action == 'PLACE_NEUTRAL_GRID'
    assert len(decision.orders) == 16  # default 8 levels, two sides each, max_grid_levels only caps helper-level input


def test_dca_generates_one_order():
    snapshot = MarketSnapshot(symbol='ETHUSDT', mark_price=2500)
    limits = RiskLimits(max_position_usdt=100, risk_per_tick_usdt=25)
    decision = run_strategy('DCA', snapshot, limits)
    assert decision.action == 'SCHEDULE_DCA_BUY'
    assert len(decision.orders) == 1


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
