from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationStep:
    name: str
    required: bool
    instruction: str
    success_criteria: str


TESTNET_VALIDATION_STEPS = [
    ValidationStep('credential_scope', True, 'Create exchange API key with trading-only permission and no withdrawal permission.', 'Key validates and withdrawal permission is absent.'),
    ValidationStep('ip_allowlist', True, 'Bind API key to fixed cloud server IP where exchange supports allowlisting.', 'Requests from server succeed; other IPs fail.'),
    ValidationStep('dry_run_tick', True, 'Run every bot in dry-run for at least 24 ticks.', 'No duplicate idempotency keys and all audit logs are present.'),
    ValidationStep('testnet_order', True, 'Enable testnet/sandbox adapter and submit minimum-size order.', 'Order is accepted, visible on exchange, and reconciled locally.'),
    ValidationStep('cancel_reduce_only', True, 'Test cancel and reduce-only flows where supported.', 'No orphan orders and no unexpected exposure increase.'),
]

MAINNET_VALIDATION_STEPS = [
    ValidationStep('small_size_mainnet', True, 'Use the smallest mainnet order size supported by the exchange.', 'Order lifecycle is fully logged and reconciled.'),
    ValidationStep('loss_cap', True, 'Set hard daily loss cap and max position below production target.', 'Risk module blocks orders above cap.'),
    ValidationStep('single_bot_single_symbol', True, 'Run one bot on one symbol before scaling.', 'No duplicate orders, no unexpected leverage, no unreconciled positions.'),
    ValidationStep('alert_delivery', True, 'Verify Telegram/Webhook/Email alerts.', 'Start, order, failure and reconciliation alerts are received.'),
]


def validation_plan() -> dict[str, list[dict[str, Any]]]:
    return {
        'testnet': [step.__dict__ for step in TESTNET_VALIDATION_STEPS],
        'small_size_mainnet': [step.__dict__ for step in MAINNET_VALIDATION_STEPS],
    }
