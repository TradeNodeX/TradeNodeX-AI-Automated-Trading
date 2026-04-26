from fastapi.testclient import TestClient

from tradenodex_aat.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get('/v1/health')
    assert response.status_code == 200
    assert response.json()['ok'] is True


def test_dashboard_contains_seed_bots():
    client = TestClient(app)
    response = client.get('/v1/dashboard')
    assert response.status_code == 200
    payload = response.json()
    assert payload['metrics']['bots'] >= 5
    assert len(payload['bots']) >= 5
    assert 'orders' in payload
    assert 'positions' in payload


def test_create_and_tick_bot():
    client = TestClient(app)
    create_response = client.post('/v1/bots', json={
        'name': 'API Test DCA',
        'type': 'DCA',
        'exchange': 'BINANCE_FUTURES',
        'symbols': ['BTCUSDT'],
        'max_position_usdt': 50,
        'risk_per_tick_usdt': 5,
        'dry_run': True
    })
    assert create_response.status_code == 200
    bot = create_response.json()
    tick_response = client.post(f"/v1/bots/{bot['id']}/tick")
    assert tick_response.status_code == 200
    payload = tick_response.json()
    assert payload['decision']['action'] in {'SCHEDULE_DCA_BUY', 'WAIT'}
    assert payload['execution']['accepted'] is True


def test_validation_plan_endpoint():
    client = TestClient(app)
    response = client.get('/v1/validation-plan')
    assert response.status_code == 200
    payload = response.json()
    assert 'testnet' in payload
    assert 'small_size_mainnet' in payload
