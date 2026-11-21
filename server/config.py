import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Loads server/.env into the environment (real environment variables take priority).
load_dotenv(Path(__file__).parent / ".env")

_DEFAULT_SQLITE = f"sqlite:///{Path(__file__).parent / 'budget_tracker.db'}"


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in ("1", "true", "yes", "on")


DATABASE_URL: str = os.environ.get("DATABASE_URL") or _DEFAULT_SQLITE

# Without SECRET_KEY set, a random key is used and every access token is invalidated on restart.
SECRET_KEY: str = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

# Access tokens are short-lived JWTs; refresh tokens are long-lived, stored hashed in the database.
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# The refresh token travels in an HttpOnly cookie. Set COOKIE_SECURE=true when served over HTTPS.
COOKIE_SECURE: bool = _bool("COOKIE_SECURE", False)
