import os

os.environ.setdefault('TRADENODEX_AAT_OPERATOR_TOKEN', 'test-token')
os.environ.setdefault('TRADENODEX_AAT_ENCRYPTION_KEY', 'test-encryption-key')
os.environ.setdefault('TRADENODEX_AAT_DB_PATH', './data/test_tradenodex_aat.sqlite3')
os.environ.setdefault('TRADENODEX_AAT_COPY_ENGINE_ENABLED', 'true')

from fastapi.testclient import TestClient

from tradenodex_aat.main import app

AUTH = {'Authorization': 'Bearer test-token'}


def test_health_endpoint_and_branding_headers():
    client = TestClient(app)
    response = client.get('/v1/health')
    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['brand'] == 'TradeNodeX'
    assert payload['copy_engine_enabled'] is True
    assert response.headers['X-TradeNodeX-Project'] == 'TradeNodeX AI Automated Trading'
    assert 'Not financial advice' in response.headers['X-TradeNodeX-Risk-Notice']


def test_legal_endpoint_contains_disclaimer():
    client = TestClient(app)
    response = client.get('/v1/legal')
    assert response.status_code == 200
    payload = response.json()
    assert payload['owner'] == 'TradeNodeX'
    assert payload['license'] == 'MIT'
    assert 'not financial advice' in payload['disclaimer'].lower()
    assert 'not affiliated' in payload['disclaimer'].lower()


def test_dashboard_contains_seed_bots_and_signal_queue_metric():
    client = TestClient(app)
    response = client.get('/v1/dashboard')
    assert response.status_code == 200
    payload = response.json()
    assert payload['metrics']['bots'] >= 5
    assert len(payload['bots']) >= 5
    assert 'orders' in payload
    assert 'positions' in payload
    assert 'signal_queue' in payload['metrics']
    assert payload['legal']['owner'] == 'TradeNodeX'


def test_write_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post('/v1/bots', json={'name': 'Unauthorized', 'type': 'DCA', 'exchange': 'BINANCE_FUTURES'})
    assert response.status_code in {401, 503}


def test_create_tick_orders_and_reconcile_dry_run_flow_with_operator_token():
    client = TestClient(app)
    account_response = client.post('/v1/accounts', headers=AUTH, json={'name': 'API Test Account', 'exchange': 'BINANCE_FUTURES', 'environment': 'TESTNET', 'dry_run': True})
    assert account_response.status_code == 200
    account = account_response.json()
    create_response = client.post('/v1/bots', headers=AUTH, json={'name': 'API Test DCA', 'type': 'DCA', 'exchange': 'BINANCE_FUTURES', 'symbols': ['BTCUSDT'], 'max_position_usdt': 50, 'risk_per_tick_usdt': 5, 'dry_run': True, 'account_id': account['id']})
    assert create_response.status_code == 200
    bot = create_response.json()
    tick_response = client.post(f"/v1/bots/{bot['id']}/tick", headers=AUTH)
    assert tick_response.status_code == 200
    payload = tick_response.json()
    assert payload['decision']['action'] in {'SCHEDULE_DCA_BUY', 'WAIT'}
    assert payload['execution']['accepted'] is True
    assert isinstance(client.get('/v1/orders').json(), list)
    reconcile_response = client.post('/v1/reconcile', headers=AUTH)
    assert reconcile_response.status_code == 200
    assert 'results' in reconcile_response.json()


def test_market_snapshot_requires_auth_but_validation_plan_is_public():
    client = TestClient(app)
    denied = client.post('/v1/market-snapshot', json={'exchange': 'BINANCE_FUTURES', 'symbol': 'BTCUSDT'})
    assert denied.status_code in {401, 503}
    allowed = client.post('/v1/market-snapshot', headers=AUTH, json={'exchange': 'BINANCE_FUTURES', 'symbol': 'BTCUSDT'})
    assert allowed.status_code == 200
    assert allowed.json()['symbol'] == 'BTCUSDT'
    response = client.get('/v1/validation-plan')
    assert response.status_code == 200
    payload = response.json()
    assert 'testnet' in payload
    assert 'small_size_mainnet' in payload


def test_copy_signal_requires_auth_and_can_be_queued():
    client = TestClient(app)
    denied = client.post('/v1/copy/signals', json={'symbol': 'BTCUSDT', 'side': 'BUY', 'notional_usdt': 5})
    assert denied.status_code in {401, 503}
    accepted = client.post('/v1/copy/signals', headers=AUTH, json={'symbol': 'BTCUSDT', 'side': 'BUY', 'order_type': 'MARKET', 'notional_usdt': 5, 'multiplier': 1, 'slippage_bps': 20})
    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload['queued'] is True
    assert 'signal_id' in payload
    metrics = client.get('/v1/copy/metrics')
    assert metrics.status_code == 200
    assert 'queue_size' in metrics.json()


def test_account_risk_budget_endpoint():
    client = TestClient(app)
    account_response = client.post('/v1/accounts', headers=AUTH, json={'name': 'Risk Budget Account', 'exchange': 'BINANCE_FUTURES', 'environment': 'TESTNET', 'dry_run': True})
    assert account_response.status_code == 200
    account = account_response.json()
    response = client.post(f"/v1/accounts/{account['id']}/risk-budget", headers=AUTH, json={'max_order_notional_usdt': 10, 'max_daily_notional_usdt': 100, 'max_position_notional_usdt': 100, 'min_free_balance_usdt': 5, 'max_slippage_bps': 20, 'rate_limit_per_minute': 10, 'failures_before_circuit_break': 2, 'circuit_break_seconds': 60})
    assert response.status_code == 200
    assert response.json()['account_id'] == account['id']
    assert response.json()['max_order_notional_usdt'] == 10
