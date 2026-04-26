import asyncio
import hashlib
import json
from typing import Any

from .credentials import ExchangeCredentials
from .exchanges import get_exchange_spec


class ExchangeAdapterError(RuntimeError):
    pass


class BaseExchangeAdapter:
    def __init__(self, exchange: str, dry_run: bool = True, credentials: ExchangeCredentials | None = None) -> None:
        self.exchange = exchange
        self.spec = get_exchange_spec(exchange)
        self.dry_run = dry_run
        self.credentials = credentials or ExchangeCredentials(api_key=None, api_secret=None)

    def make_idempotency_key(self, bot_id: str, order: dict[str, Any]) -> str:
        basis = json.dumps({'bot_id': bot_id, 'exchange': self.exchange, 'order': order}, sort_keys=True)
        return hashlib.sha256(basis.encode('utf-8')).hexdigest()

    async def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run:
            return {'dry_run': True, 'exchange': self.exchange, 'status': 'ACCEPTED_DRY_RUN', 'order': order}
        return await self.place_live_order(order)

    async def place_live_order(self, order: dict[str, Any]) -> dict[str, Any]:
        raise ExchangeAdapterError('Live native execution adapter is not implemented for this exchange yet.')

    async def fetch_positions(self) -> list[dict[str, Any]]:
        return []

    async def fetch_market_snapshot(self, symbol: str) -> dict[str, Any]:
        return {'exchange': self.exchange, 'symbol': symbol, 'mark_price': 50000.0, 'funding_rate': 0.0, 'source': 'adapter-fallback'}


class BinanceFuturesTestnetAdapter(BaseExchangeAdapter):
    def _client(self):
        if not self.credentials.ready:
            raise ExchangeAdapterError('Binance Futures Testnet credentials are missing. Configure local env or encrypted account credentials.')
        try:
            import ccxt  # type: ignore
        except Exception as exc:
            raise ExchangeAdapterError('ccxt is required for Binance Futures Testnet adapter.') from exc
        client = ccxt.binanceusdm({
            'apiKey': self.credentials.api_key,
            'secret': self.credentials.api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'future', 'adjustForTimeDifference': True},
        })
        client.set_sandbox_mode(True)
        return client

    async def place_live_order(self, order: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        symbol = _ccxt_symbol(order['symbol'])
        order_type = str(order.get('type') or 'limit').lower()
        side = str(order['side']).lower()
        amount = float(order['qty'])
        price = order.get('price')
        params = {'newClientOrderId': order.get('client_order_id')} if order.get('client_order_id') else {}
        if order.get('reduce_only'):
            params['reduceOnly'] = True
        if order.get('post_only'):
            params['postOnly'] = True
        def _place():
            return client.create_order(symbol=symbol, type=order_type, side=side, amount=amount, price=price, params=params)
        response = await asyncio.to_thread(_place)
        return {'dry_run': False, 'exchange': self.exchange, 'status': 'SENT', 'raw': response}

    async def fetch_positions(self) -> list[dict[str, Any]]:
        client = self._client()
        def _fetch():
            return client.fetch_positions()
        rows = await asyncio.to_thread(_fetch)
        out = []
        for row in rows:
            contracts = float(row.get('contracts') or row.get('contractSize') or 0)
            if contracts == 0:
                continue
            out.append({
                'symbol': _plain_symbol(row.get('symbol') or ''),
                'side': row.get('side') or 'NET',
                'qty': contracts,
                'entry_price': row.get('entryPrice'),
                'mark_price': row.get('markPrice'),
                'unrealized_pnl': row.get('unrealizedPnl'),
            })
        return out

    async def fetch_market_snapshot(self, symbol: str) -> dict[str, Any]:
        client = self._client()
        ccxt_symbol = _ccxt_symbol(symbol)
        def _fetch():
            ticker = client.fetch_ticker(ccxt_symbol)
            funding = client.fetch_funding_rate(ccxt_symbol)
            return ticker, funding
        ticker, funding = await asyncio.to_thread(_fetch)
        return {
            'exchange': self.exchange,
            'symbol': symbol,
            'mark_price': float(ticker.get('last') or ticker.get('mark') or ticker.get('close')),
            'funding_rate': float(funding.get('fundingRate') or 0),
            'bid': ticker.get('bid'),
            'ask': ticker.get('ask'),
            'source': 'binanceusdm-testnet-ccxt',
        }


class CcxtExchangeAdapter(BaseExchangeAdapter):
    async def place_live_order(self, order: dict[str, Any]) -> dict[str, Any]:
        raise ExchangeAdapterError('Live order placement for this exchange is blocked until its adapter has passed testnet validation.')


def _ccxt_symbol(symbol: str) -> str:
    compact = symbol.replace('/', '').replace(':USDT', '').upper()
    if compact.endswith('USDT'):
        return f'{compact[:-4]}/USDT:USDT'
    return symbol


def _plain_symbol(symbol: str) -> str:
    return symbol.replace('/', '').replace(':USDT', '').upper()


def build_adapter(exchange: str, dry_run: bool = True, credentials: ExchangeCredentials | None = None) -> BaseExchangeAdapter:
    if exchange == 'BINANCE_FUTURES' and credentials and credentials.environment == 'TESTNET':
        return BinanceFuturesTestnetAdapter(exchange, dry_run=dry_run, credentials=credentials)
    return CcxtExchangeAdapter(exchange, dry_run=dry_run, credentials=credentials)
