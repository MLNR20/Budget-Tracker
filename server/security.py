import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"

password_hash = PasswordHash.recommended()  # Argon2id

# Verified against when the email is unknown, so login timing doesn't reveal which emails exist.
_DUMMY_HASH = password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if hashed is None:
        password_hash.verify(password, _DUMMY_HASH)
        return False
    return password_hash.verify(password, hashed)


# ---- access tokens: short-lived, stateless JWTs ----------------------------------------------

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Returns the user id, or None if the token is invalid, expired, or not an access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            return None
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


# ---- refresh tokens: opaque random strings, only a SHA-256 hash is stored --------------------

def hash_token(raw_token: str) -> str:
    # A fast hash is fine here: the token is 384 bits of randomness, not a guessable password.
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_token() -> tuple[str, str]:
    """Returns (raw_token_for_the_client, hash_to_store). Used for refresh and reset tokens."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


hash_refresh_token = hash_token
generate_refresh_token = generate_token
