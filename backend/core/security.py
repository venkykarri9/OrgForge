"""Token encryption/decryption for stored OAuth tokens using Fernet symmetric encryption."""
import base64
from cryptography.fernet import Fernet
from .config import get_settings

settings = get_settings()


def _get_fernet() -> Fernet:
    key = settings.token_encryption_key
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(token: str) -> str:
    """Encrypt a plaintext OAuth token for database storage."""
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored token back to plaintext."""
    return _get_fernet().decrypt(encrypted.encode()).decode()


def generate_encryption_key() -> str:
    """Generate a new Fernet key (run once during setup)."""
    return Fernet.generate_key().decode()
