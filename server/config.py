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

# Which calendar day "today" is, for recurring transactions (a rule due on the 1st should fire on
# the user's 1st, not the server's UTC 1st). IANA name, e.g. "Asia/Manila".
APP_TIMEZONE: str = os.environ.get("APP_TIMEZONE", "Asia/Manila")

# Password reset: single-use link, valid for this many minutes.
PASSWORD_RESET_EXPIRE_MINUTES: int = int(os.environ.get("PASSWORD_RESET_EXPIRE_MINUTES", "30"))
# Where the front end lives; reset links point here.
FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Outgoing email (for reset links). If SMTP_HOST is empty, emails are NOT sent: the reset link is
# written to the server log instead, which is only meant for local development.
SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER: str = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM: str = os.environ.get("SMTP_FROM", "") or SMTP_USER or "no-reply@budget-tracker.local"

# The refresh token travels in an HttpOnly cookie. Set COOKIE_SECURE=true when served over HTTPS.
COOKIE_SECURE: bool = _bool("COOKIE_SECURE", False)
