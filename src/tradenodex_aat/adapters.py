import asyncio
import hashlib
import json
from typing import Any

from .credentials import ExchangeCredentials
from .exchanges import get_exchange_spec
from .order_utils import normalize_order_status, safe_float
from .settings import get_settings


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

    async def fetch_order_by_client_id(self, symbol: str, client_order_id: str) -> dict[str, Any] | None:
        return None

    async def fetch_positions(self) -> list[dict[str, Any]]:
        return []

    async def fetch_open_orders(self) -> list[dict[str, Any]]:
        return []

    async def fetch_balance(self) -> dict[str, Any]:
        return {}

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

    def _prepare_order(self, client, order: dict[str, Any]) -> dict[str, Any]:
        symbol = _ccxt_symbol(order['symbol'])
        client.load_markets()
        market = client.market(symbol)
        amount = float(order['qty'])
        price = order.get('price')
        amount_precise = float(client.amount_to_precision(symbol, amount))
        price_precise = float(client.price_to_precision(symbol, price)) if price is not None else None
        min_amount = safe_float(market.get('limits', {}).get('amount', {}).get('min'))
        min_cost = safe_float(market.get('limits', {}).get('cost', {}).get('min'))
        notional = amount_precise * safe_float(price_precise or order.get('reference_price') or order.get('mark_price') or 0)
        if min_amount and amount_precise < min_amount:
            raise ExchangeAdapterError(f'Order amount {amount_precise} is below exchange min amount {min_amount}.')
        if min_cost and notional and notional < min_cost:
            raise ExchangeAdapterError(f'Order notional {notional} is below exchange min cost {min_cost}.')
        return {'symbol': symbol, 'amount': amount_precise, 'price': price_precise}

    async def configure_symbol(self, symbol: str) -> dict[str, Any]:
        settings = get_settings()
        client = self._client()
        ccxt_symbol = _ccxt_symbol(symbol)
        leverage = int(settings.binance_testnet_default_leverage)
        margin_mode = settings.binance_testnet_margin_mode.lower()
        def _configure():
            client.load_markets()
            results = {'symbol': ccxt_symbol, 'leverage': leverage, 'margin_mode': margin_mode}
            try:
                results['set_margin_mode'] = client.set_margin_mode(margin_mode, ccxt_symbol)
            except Exception as exc:
                results['set_margin_mode_warning'] = str(exc)
            try:
                results['set_leverage'] = client.set_leverage(leverage, ccxt_symbol)
            except Exception as exc:
                results['set_leverage_warning'] = str(exc)
            return results
        return await asyncio.to_thread(_configure)

    async def place_live_order(self, order: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        prepared = await asyncio.to_thread(self._prepare_order, client, order)
        order_type = str(order.get('type') or 'LIMIT').lower()
        side = str(order['side']).lower()
        params = {'newClientOrderId': order.get('client_order_id')} if order.get('client_order_id') else {}
        if order.get('reduce_only'):
            params['reduceOnly'] = True
        if order.get('post_only'):
            params['postOnly'] = True
        def _place():
            return client.create_order(symbol=prepared['symbol'], type=order_type, side=side, amount=prepared['amount'], price=prepared['price'], params=params)
        response = await asyncio.to_thread(_place)
        return {'dry_run': False, 'exchange': self.exchange, 'status': 'SENT', 'raw': response}

    async def fetch_order_by_client_id(self, symbol: str, client_order_id: str) -> dict[str, Any] | None:
        client = self._client()
        ccxt_symbol = _ccxt_symbol(symbol)
        def _fetch():
            try:
                return client.fetch_order(client_order_id, ccxt_symbol, {'origClientOrderId': client_order_id})
            except Exception:
                try:
                    orders = client.fetch_open_orders(ccxt_symbol)
                    return next((order for order in orders if str(order.get('clientOrderId') or order.get('clientOrderID') or order.get('info', {}).get('clientOrderId')) == client_order_id), None)
                except Exception:
                    return None
        row = await asyncio.to_thread(_fetch)
        if not row:
            return None
        return {'exchange': self.exchange, 'status': normalize_order_status(row.get('status')), 'raw': row}

    async def fetch_positions(self) -> list[dict[str, Any]]:
        client = self._client()
        rows = await asyncio.to_thread(client.fetch_positions)
        out = []
        for row in rows:
            contracts = safe_float(row.get('contracts') or row.get('contractSize') or row.get('info', {}).get('positionAmt'))
            if contracts == 0:
                continue
            out.append({'symbol': _plain_symbol(row.get('symbol') or ''), 'side': row.get('side') or 'NET', 'qty': contracts, 'entry_price': row.get('entryPrice'), 'mark_price': row.get('markPrice'), 'unrealized_pnl': row.get('unrealizedPnl')})
        return out

    async def fetch_open_orders(self) -> list[dict[str, Any]]:
        client = self._client()
        rows = await asyncio.to_thread(client.fetch_open_orders)
        return [{'symbol': _plain_symbol(row.get('symbol') or ''), 'side': row.get('side'), 'qty': row.get('amount'), 'price': row.get('price'), 'status': normalize_order_status(row.get('status')), 'client_order_id': row.get('clientOrderId') or row.get('info', {}).get('clientOrderId'), 'raw': row} for row in rows]

    async def fetch_balance(self) -> dict[str, Any]:
        client = self._client()
        row = await asyncio.to_thread(client.fetch_balance)
        return {'USDT': row.get('USDT', {}), 'raw': row}

    async def fetch_market_snapshot(self, symbol: str) -> dict[str, Any]:
        client = self._client()
        ccxt_symbol = _ccxt_symbol(symbol)
        def _fetch():
            ticker = client.fetch_ticker(ccxt_symbol)
            funding = client.fetch_funding_rate(ccxt_symbol)
            return ticker, funding
        ticker, funding = await asyncio.to_thread(_fetch)
        mark_price = safe_float(ticker.get('last') or ticker.get('mark') or ticker.get('close'))
        return {'exchange': self.exchange, 'symbol': symbol, 'mark_price': mark_price, 'funding_rate': safe_float(funding.get('fundingRate')), 'bid': ticker.get('bid'), 'ask': ticker.get('ask'), 'source': 'binanceusdm-testnet-ccxt'}


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
