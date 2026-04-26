import asyncio
from typing import Any

from .adapters import BaseExchangeAdapter, ExchangeAdapterError, _plain_symbol
from .order_utils import normalize_order_status, safe_float


CCXT_IDS = {
    'BINANCE_FUTURES': 'binanceusdm',
    'BYBIT_LINEAR': 'bybit',
    'OKX_SWAP': 'okx',
    'KRAKEN_FUTURES': 'krakenfutures',
    'BITMEX': 'bitmex',
    'GATEIO_FUTURES': 'gateio',
    'COINBASE_ADVANCED': 'coinbase',
}

DEFAULT_TYPE = {
    'BINANCE_FUTURES': 'future',
    'BYBIT_LINEAR': 'swap',
    'OKX_SWAP': 'swap',
    'KRAKEN_FUTURES': 'future',
    'BITMEX': 'swap',
    'GATEIO_FUTURES': 'swap',
    'COINBASE_ADVANCED': 'spot',
}


def normalize_symbol(exchange: str, symbol: str) -> str:
    raw = symbol.replace('/', '').replace(':USDT', '').upper()
    if exchange == 'COINBASE_ADVANCED':
        if raw.endswith('USD'):
            return f'{raw[:-3]}/USD'
        if raw.endswith('USDT'):
            return f'{raw[:-4]}/USDT'
    if raw.endswith('USDT'):
        return f'{raw[:-4]}/USDT:USDT'
    if raw.endswith('USD'):
        return f'{raw[:-3]}/USD'
    return symbol


class ControlledMainnetCcxtAdapter(BaseExchangeAdapter):
    def _client(self):
        if not self.credentials.ready:
            raise ExchangeAdapterError(f'{self.exchange} mainnet credentials are missing.')
        try:
            import ccxt  # type: ignore
        except Exception as exc:
            raise ExchangeAdapterError('ccxt is required for controlled mainnet adapters.') from exc
        exchange_id = CCXT_IDS.get(self.exchange)
        if not exchange_id:
            raise ExchangeAdapterError(f'Unsupported controlled mainnet exchange: {self.exchange}')
        klass = getattr(ccxt, exchange_id)
        params: dict[str, Any] = {
            'apiKey': self.credentials.api_key,
            'secret': self.credentials.api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': DEFAULT_TYPE.get(self.exchange, 'swap'), 'adjustForTimeDifference': True},
        }
        if self.credentials.api_passphrase:
            params['password'] = self.credentials.api_passphrase
        return klass(params)

    def _resolve_market_symbol(self, client, symbol: str) -> str:
        preferred = normalize_symbol(self.exchange, symbol)
        client.load_markets()
        if preferred in client.markets:
            return preferred
        fallback = preferred.replace(':USDT', '')
        if fallback in client.markets:
            return fallback
        raw = symbol.upper().replace('/', '').replace(':USDT', '')
        for market_symbol in client.markets:
            compact = market_symbol.upper().replace('/', '').replace(':USDT', '')
            if compact == raw:
                return market_symbol
        raise ExchangeAdapterError(f'Symbol {symbol} is not available on {self.exchange}.')

    def _prepare_order(self, client, order: dict[str, Any]) -> dict[str, Any]:
        symbol = self._resolve_market_symbol(client, order['symbol'])
        market = client.market(symbol)
        amount = float(order['qty'])
        price = order.get('price')
        amount_precise = float(client.amount_to_precision(symbol, amount))
        price_precise = float(client.price_to_precision(symbol, price)) if price is not None else None
        min_amount = safe_float(market.get('limits', {}).get('amount', {}).get('min'))
        min_cost = safe_float(market.get('limits', {}).get('cost', {}).get('min'))
        reference_price = safe_float(price_precise or order.get('reference_price') or order.get('mark_price') or 0)
        notional = amount_precise * reference_price
        if min_amount and amount_precise < min_amount:
            raise ExchangeAdapterError(f'Order amount {amount_precise} is below exchange min amount {min_amount}.')
        if min_cost and notional and notional < min_cost:
            raise ExchangeAdapterError(f'Order notional {notional} is below exchange min cost {min_cost}.')
        return {'symbol': symbol, 'amount': amount_precise, 'price': price_precise}

    async def configure_symbol(self, symbol: str, leverage: int = 1, margin_mode: str = 'isolated') -> dict[str, Any]:
        client = self._client()
        def _configure():
            resolved = self._resolve_market_symbol(client, symbol)
            result: dict[str, Any] = {'exchange': self.exchange, 'symbol': resolved, 'leverage': leverage, 'margin_mode': margin_mode}
            if hasattr(client, 'set_margin_mode'):
                try:
                    result['set_margin_mode'] = client.set_margin_mode(margin_mode.lower(), resolved)
                except Exception as exc:
                    result['set_margin_mode_warning'] = str(exc)
            if hasattr(client, 'set_leverage'):
                try:
                    result['set_leverage'] = client.set_leverage(leverage, resolved)
                except Exception as exc:
                    result['set_leverage_warning'] = str(exc)
            return result
        return await asyncio.to_thread(_configure)

    async def place_live_order(self, order: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        prepared = await asyncio.to_thread(self._prepare_order, client, order)
        params: dict[str, Any] = {}
        client_id = order.get('client_order_id')
        if client_id:
            params.update({'clientOrderId': client_id, 'newClientOrderId': client_id, 'clOrdID': client_id, 'clOrdId': client_id})
        if order.get('reduce_only'):
            params['reduceOnly'] = True
        if order.get('post_only'):
            params['postOnly'] = True
        def _place():
            return client.create_order(
                symbol=prepared['symbol'],
                type=str(order.get('type') or 'LIMIT').lower(),
                side=str(order['side']).lower(),
                amount=prepared['amount'],
                price=prepared['price'],
                params=params,
            )
        response = await asyncio.to_thread(_place)
        return {'dry_run': False, 'exchange': self.exchange, 'status': 'SENT', 'raw': response}

    async def fetch_order_by_client_id(self, symbol: str, client_order_id: str) -> dict[str, Any] | None:
        client = self._client()
        def _fetch():
            resolved = self._resolve_market_symbol(client, symbol)
            try:
                return client.fetch_order(client_order_id, resolved, {'clientOrderId': client_order_id, 'origClientOrderId': client_order_id, 'clOrdID': client_order_id, 'clOrdId': client_order_id})
            except Exception:
                try:
                    rows = client.fetch_open_orders(resolved)
                    return next((row for row in rows if str(row.get('clientOrderId') or row.get('info', {}).get('clientOrderId') or row.get('info', {}).get('clOrdID') or row.get('info', {}).get('clOrdId')) == client_order_id), None)
                except Exception:
                    return None
        row = await asyncio.to_thread(_fetch)
        return {'exchange': self.exchange, 'status': normalize_order_status(row.get('status')), 'raw': row} if row else None

    async def fetch_positions(self) -> list[dict[str, Any]]:
        client = self._client()
        try:
            rows = await asyncio.to_thread(client.fetch_positions)
        except Exception:
            return []
        out = []
        for row in rows:
            qty = safe_float(row.get('contracts') or row.get('contractSize') or row.get('info', {}).get('positionAmt') or row.get('info', {}).get('size'))
            if qty == 0:
                continue
            out.append({'symbol': _plain_symbol(row.get('symbol') or ''), 'side': row.get('side') or 'NET', 'qty': qty, 'entry_price': row.get('entryPrice'), 'mark_price': row.get('markPrice'), 'unrealized_pnl': row.get('unrealizedPnl')})
        return out

    async def fetch_open_orders(self) -> list[dict[str, Any]]:
        client = self._client()
        try:
            rows = await asyncio.to_thread(client.fetch_open_orders)
        except Exception:
            return []
        return [{'symbol': _plain_symbol(row.get('symbol') or ''), 'side': row.get('side'), 'qty': row.get('amount'), 'price': row.get('price'), 'status': normalize_order_status(row.get('status')), 'client_order_id': row.get('clientOrderId') or row.get('info', {}).get('clientOrderId') or row.get('info', {}).get('clOrdID') or row.get('info', {}).get('clOrdId'), 'raw': row} for row in rows]

    async def fetch_balance(self) -> dict[str, Any]:
        client = self._client()
        try:
            return await asyncio.to_thread(client.fetch_balance)
        except Exception:
            return {}

    async def fetch_market_snapshot(self, symbol: str) -> dict[str, Any]:
        client = self._client()
        def _fetch():
            resolved = self._resolve_market_symbol(client, symbol)
            ticker = client.fetch_ticker(resolved)
            funding = {}
            if hasattr(client, 'fetch_funding_rate'):
                try:
                    funding = client.fetch_funding_rate(resolved)
                except Exception:
                    funding = {}
            return ticker, funding
        ticker, funding = await asyncio.to_thread(_fetch)
        mark_price = safe_float(ticker.get('last') or ticker.get('mark') or ticker.get('close'))
        return {'exchange': self.exchange, 'symbol': symbol, 'mark_price': mark_price, 'funding_rate': safe_float(funding.get('fundingRate')), 'bid': ticker.get('bid'), 'ask': ticker.get('ask'), 'source': f'{self.exchange.lower()}-controlled-mainnet-ccxt'}
