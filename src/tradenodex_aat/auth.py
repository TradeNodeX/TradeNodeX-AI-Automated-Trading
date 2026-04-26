import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from .settings import get_settings


PUBLIC_READ_PATHS = {'/', '/v1/health', '/v1/dashboard', '/v1/bots', '/v1/accounts', '/v1/orders', '/v1/positions', '/v1/logs', '/v1/validation-plan'}


def require_operator_token(authorization: Annotated[str | None, Header()] = None, x_operator_token: Annotated[str | None, Header()] = None) -> None:
    settings = get_settings()
    expected = settings.operator_token
    if not expected or expected == 'change-me':
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='operator_token_not_configured')
    supplied = None
    if authorization and authorization.lower().startswith('bearer '):
        supplied = authorization.split(' ', 1)[1].strip()
    elif x_operator_token:
        supplied = x_operator_token.strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid_operator_token')
