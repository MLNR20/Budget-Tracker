import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Loads server/.env into the environment (real environment variables take priority).
load_dotenv(Path(__file__).parent / ".env")

_DEFAULT_SQLITE = f"sqlite:///{Path(__file__).parent / 'budget_tracker.db'}"

DATABASE_URL: str = os.environ.get("DATABASE_URL") or _DEFAULT_SQLITE

# Without SECRET_KEY set, a random key is used and every login is invalidated on restart.
SECRET_KEY: str = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
