from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import get_settings

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("not-a-real-password")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def fake_verify() -> None:
    """Spend similar time for unknown emails so login timing does not reveal them."""
    verify_password("x", _DUMMY_HASH)


def create_token(user_id: int, minutes: int | None = None) -> str:
    settings = get_settings()
    lifetime = settings.access_token_minutes if minutes is None else minutes
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=lifetime)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM],
                      options={"require": ["exp", "sub"]})
