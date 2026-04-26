import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .settings import get_settings


def _derive_key(seed: str) -> bytes:
    digest = hashlib.sha256(seed.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    settings = get_settings()
    seed = settings.encryption_key or settings.operator_token
    if seed == 'change-me':
        seed = 'tradenodex-local-development-key-change-before-production'
    return Fernet(_derive_key(seed))


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return get_fernet().encrypt(value.encode('utf-8')).decode('utf-8')


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return get_fernet().decrypt(value.encode('utf-8')).decode('utf-8')
    except InvalidToken as exc:
        raise ValueError('Secret decryption failed. Check TRADENODEX_AAT_ENCRYPTION_KEY.') from exc


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return '****'
    return f'{value[:4]}****{value[-4:]}'
