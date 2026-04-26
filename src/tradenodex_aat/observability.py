import json
import time
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx: ContextVar[str] = ContextVar('request_id', default='-')


def request_id() -> str:
    return request_id_ctx.get()


def log_json(event: str, **fields) -> None:
    print(json.dumps({'event': event, 'request_id': request_id(), **fields}, default=str, separators=(',', ':')), flush=True)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get('x-request-id') or str(uuid4())
        request_id_ctx.set(rid)
        start = time.perf_counter()
        response = await call_next(request)
        response.headers['x-request-id'] = rid
        response.headers['x-process-time-ms'] = str(round((time.perf_counter() - start) * 1000, 2))
        log_json('http_request', method=request.method, path=request.url.path, status=response.status_code)
        return response
