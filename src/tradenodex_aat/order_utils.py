from typing import Any


def extract_exchange_order_id(raw_response_json: str | None) -> str | None:
    if not raw_response_json:
        return None
    try:
        import json
        data = json.loads(raw_response_json)
    except Exception:
        return None
    raw = data.get('raw') if isinstance(data, dict) else None
    if isinstance(raw, dict):
        return str(raw.get('id') or raw.get('orderId') or raw.get('clientOrderId') or '') or None
    return None


def normalize_order_status(status: str | None) -> str:
    value = (status or '').upper()
    if value in {'CLOSED', 'FILLED'}:
        return 'FILLED'
    if value in {'CANCELED', 'CANCELLED'}:
        return 'CANCELED'
    if value in {'OPEN', 'NEW'}:
        return 'SENT'
    if value in {'ACCEPTED_DRY_RUN'}:
        return value
    return value or 'UNKNOWN'


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
