import os

os.environ.setdefault('TRADENODEX_AAT_OPERATOR_TOKEN', 'test-token')
os.environ.setdefault('TRADENODEX_AAT_ENCRYPTION_KEY', 'test-encryption-key')
os.environ.setdefault('TRADENODEX_AAT_DB_PATH', './data/test_tradenodex_aat.sqlite3')

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


def test_dashboard_contains_seed_bots_and_legal_payload():
    client = TestClient(app)
    response = client.get('/v1/dashboard')
    assert response.status_code == 200
    payload = response.json()
    assert payload['metrics']['bots'] >= 5
    assert len(payload['bots']) >= 5
    assert 'orders' in payload
    assert 'positions' in payload
    assert payload['legal']['owner'] == 'TradeNodeX'


def test_write_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post('/v1/bots', json={'name': 'Unauthorized', 'type': 'DCA', 'exchange': 'BINANCE_FUTURES'})
    assert response.status_code in {401, 503}


def test_create_tick_orders_and_reconcile_dry_run_flow_with_operator_token():
    client = TestClient(app)
    account_response = client.post('/v1/accounts', headers=AUTH, json={
        'name': 'API Test Account',
        'exchange': 'BINANCE_FUTURES',
        'environment': 'TESTNET',
        'dry_run': True,
    })
    assert account_response.status_code == 200
    account = account_response.json()
    create_response = client.post('/v1/bots', headers=AUTH, json={
        'name': 'API Test DCA',
        'type': 'DCA',
        'exchange': 'BINANCE_FUTURES',
        'symbols': ['BTCUSDT'],
        'max_position_usdt': 50,
        'risk_per_tick_usdt': 5,
        'dry_run': True,
        'account_id': account['id'],
    })
    assert create_response.status_code == 200
    bot = create_response.json()
    tick_response = client.post(f"/v1/bots/{bot['id']}/tick", headers=AUTH)
    assert tick_response.status_code == 200
    payload = tick_response.json()
    assert payload['decision']['action'] in {'SCHEDULE_DCA_BUY', 'WAIT'}
    assert payload['execution']['accepted'] is True
    orders_response = client.get('/v1/orders')
    assert orders_response.status_code == 200
    assert isinstance(orders_response.json(), list)
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
