import base64
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


def generate_key() -> str:
    return Fernet.generate_key().decode()


def _get_fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY is not configured")
    try:
        key = settings.ENCRYPTION_KEY.encode()
        return Fernet(key)
    except Exception as exc:
        raise ValueError(f"Invalid ENCRYPTION_KEY: {exc}") from exc


def encrypt_value(plaintext: str) -> str:
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str | None:
    try:
        fernet = _get_fernet()
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.warning("Failed to decrypt value: invalid or tampered ciphertext")
        return None
    except ValueError:
        raise
    except Exception as exc:
        logger.warning(f"Unexpected decryption failure: {exc}")
        return None
