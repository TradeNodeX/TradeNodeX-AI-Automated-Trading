from dataclasses import dataclass
from typing import Any

from .account_controls import get_account_risk_budget
from .credentials import ExchangeCredentials
from .settings import get_settings


@dataclass(frozen=True)
class MainnetGateResult:
    allowed: bool
    reason: str
    checks: dict[str, Any]


def evaluate_mainnet_gate(account: dict[str, Any], credentials: ExchangeCredentials) -> MainnetGateResult:
    settings = get_settings()
    exchange = account['exchange']
    checks = {
        'global_live_gate': settings.enable_live_trading,
        'exchange_mainnet_flag': settings.mainnet_enabled_for_exchange(exchange),
        'account_environment_mainnet': account.get('environment') == 'MAINNET',
        'account_dry_run_false': account.get('dry_run') is False,
        'credentials_ready': credentials.ready,
        'account_budget_required': settings.mainnet_requires_account_budget,
        'account_budget_exists': False,
    }
    if not checks['global_live_gate']:
        return MainnetGateResult(False, 'global_live_trading_disabled', checks)
    if not checks['exchange_mainnet_flag']:
        return MainnetGateResult(False, f'{exchange.lower()}_mainnet_flag_disabled', checks)
    if not checks['account_environment_mainnet']:
        return MainnetGateResult(False, 'account_environment_is_not_mainnet', checks)
    if not checks['account_dry_run_false']:
        return MainnetGateResult(False, 'account_is_still_dry_run', checks)
    if not checks['credentials_ready']:
        return MainnetGateResult(False, 'mainnet_credentials_missing', checks)
    if settings.mainnet_requires_account_budget:
        try:
            budget = get_account_risk_budget(account['id'])
            checks['account_budget_exists'] = bool(budget and float(budget.get('max_order_notional_usdt', 0)) > 0)
        except Exception:
            checks['account_budget_exists'] = False
        if not checks['account_budget_exists']:
            return MainnetGateResult(False, 'account_risk_budget_missing', checks)
    return MainnetGateResult(True, 'ok', checks)
