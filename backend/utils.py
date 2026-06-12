import hashlib
import hmac
import secrets
from typing import Optional


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 150000)
    return salt, hashed.hex()


def verify_password(password: str, salt: str, hashed_password: str) -> bool:
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 150000)
    return hmac.compare_digest(derived.hex(), hashed_password)


def generate_token() -> str:
    return secrets.token_urlsafe(32)
