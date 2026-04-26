from starlette.middleware.base import BaseHTTPMiddleware

from .branding import COPYRIGHT, OWNER, PROJECT_NAME


class TradeNodeXBrandingHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['X-TradeNodeX-Project'] = PROJECT_NAME
        response.headers['X-TradeNodeX-Owner'] = OWNER
        response.headers['X-TradeNodeX-Copyright'] = COPYRIGHT
        response.headers['X-TradeNodeX-Risk-Notice'] = 'Not financial advice. Dry-run and testnet validation first.'
        return response
