import os

os.environ.setdefault('TRADENODEX_AAT_OPERATOR_TOKEN', 'test-token')
os.environ.setdefault('TRADENODEX_AAT_ENCRYPTION_KEY', 'test-encryption-key')
os.environ.setdefault('TRADENODEX_AAT_DB_PATH', './data/test_tradenodex_aat.sqlite3')

from tradenodex_aat.credentials import ExchangeCredentials
from tradenodex_aat.mainnet_gate import evaluate_mainnet_gate


EXCHANGES = [
    'BINANCE_FUTURES',
    'BYBIT_LINEAR',
    'OKX_SWAP',
    'KRAKEN_FUTURES',
    'BITMEX',
    'GATEIO_FUTURES',
    'COINBASE_ADVANCED',
]


def test_all_mainnet_exchanges_are_blocked_by_default():
    creds = ExchangeCredentials(api_key='k', api_secret='s', environment='MAINNET')
    for exchange in EXCHANGES:
        account = {'id': f'acct-{exchange}', 'exchange': exchange, 'environment': 'MAINNET', 'dry_run': False}
        result = evaluate_mainnet_gate(account, creds)
        assert result.allowed is False
        assert result.reason in {'global_live_trading_disabled', f'{exchange.lower()}_mainnet_flag_disabled'}


def test_mainnet_gate_rejects_dry_run_account_even_with_credentials():
    creds = ExchangeCredentials(api_key='k', api_secret='s', environment='MAINNET')
    account = {'id': 'acct-mainnet', 'exchange': 'BINANCE_FUTURES', 'environment': 'MAINNET', 'dry_run': True}
    result = evaluate_mainnet_gate(account, creds)
    assert result.allowed is False
    assert result.reason in {'global_live_trading_disabled', 'binance_futures_mainnet_flag_disabled', 'account_is_still_dry_run'}


def test_mainnet_gate_rejects_missing_credentials():
    creds = ExchangeCredentials(api_key=None, api_secret=None, environment='MAINNET')
    account = {'id': 'acct-mainnet', 'exchange': 'BINANCE_FUTURES', 'environment': 'MAINNET', 'dry_run': False}
    result = evaluate_mainnet_gate(account, creds)
    assert result.allowed is False
