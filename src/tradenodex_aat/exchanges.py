from dataclasses import dataclass
from enum import StrEnum

class ExchangeCode(StrEnum):
    BINANCE_FUTURES = 'BINANCE_FUTURES'
    BYBIT_LINEAR = 'BYBIT_LINEAR'
    OKX_SWAP = 'OKX_SWAP'
    KRAKEN_FUTURES = 'KRAKEN_FUTURES'
    BITMEX = 'BITMEX'
    GATEIO_FUTURES = 'GATEIO_FUTURES'
    COINBASE_ADVANCED = 'COINBASE_ADVANCED'

@dataclass(frozen=True)
class ExchangeSpec:
    code: ExchangeCode
    label: str
    product_scope: str
    ccxt_id: str | None
    private_stream: str
    requires_passphrase: bool = False
    supports_funding: bool = True
    supports_spot_grid: bool = False

EXCHANGE_SPECS: dict[str, ExchangeSpec] = {
    'BINANCE_FUTURES': ExchangeSpec(ExchangeCode.BINANCE_FUTURES, 'Binance Futures', 'USD-M perpetual / futures', 'binanceusdm', 'private websocket', supports_spot_grid=True),
    'BYBIT_LINEAR': ExchangeSpec(ExchangeCode.BYBIT_LINEAR, 'Bybit Linear', 'USDT linear perpetual', 'bybit', 'private websocket'),
    'OKX_SWAP': ExchangeSpec(ExchangeCode.OKX_SWAP, 'OKX Swap', 'swap / derivatives', 'okx', 'private websocket + REST fallback', True),
    'KRAKEN_FUTURES': ExchangeSpec(ExchangeCode.KRAKEN_FUTURES, 'Kraken Futures', 'futures / derivatives', 'krakenfutures', 'private websocket + REST fallback'),
    'BITMEX': ExchangeSpec(ExchangeCode.BITMEX, 'BitMEX', 'perpetual / derivatives', 'bitmex', 'private websocket + REST fallback'),
    'GATEIO_FUTURES': ExchangeSpec(ExchangeCode.GATEIO_FUTURES, 'Gate.io Futures', 'USDT futures', 'gateio', 'private websocket + REST fallback', supports_spot_grid=True),
    'COINBASE_ADVANCED': ExchangeSpec(ExchangeCode.COINBASE_ADVANCED, 'Coinbase Advanced', 'advanced / derivatives-compatible', 'coinbaseadvanced', 'private websocket + REST fallback', supports_funding=False, supports_spot_grid=True),
}

def get_exchange_spec(code: str) -> ExchangeSpec:
    try:
        return EXCHANGE_SPECS[code]
    except KeyError as exc:
        raise ValueError(f'Unsupported exchange: {code}') from exc

def validate_strategy_exchange(bot_type: str, exchange: str) -> tuple[bool, str]:
    spec = get_exchange_spec(exchange)
    if bot_type == 'FUNDING_ARBITRAGE' and not spec.supports_funding:
        return False, f'{spec.label} is not enabled for funding-rate arbitrage in v1.'
    if bot_type == 'CONSERVATIVE_SPOT_GRID' and not spec.supports_spot_grid:
        return False, f'{spec.label} spot-grid path is not declared stable in v1; use Binance/Gate/Coinbase or extend adapter.'
    return True, 'ok'
