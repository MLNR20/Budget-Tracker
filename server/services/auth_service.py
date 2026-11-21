from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from entities.base_entity import utc_now
from entities.refresh_token import RefreshToken
from entities.user import User
from repositories import RefreshTokenRepository, UserRepository
from security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from services.exceptions import AuthenticationError

# Two requests can race with the same refresh token (e.g. two tabs). A token rotated this recently
# is simply rejected; replaying one rotated longer ago is treated as theft and kills all sessions.
REUSE_GRACE = timedelta(seconds=10)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str  # raw value, for the cookie only; never stored
    expires_in: int  # access token lifetime in seconds


def _aware(value: datetime) -> datetime:
    # SQLite returns naive datetimes; everything here is UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class AuthService:
    def __init__(self, users: UserRepository, tokens: RefreshTokenRepository):
        self.users = users
        self.tokens = tokens

    def login(self, email: str, password: str) -> TokenPair:
        user = self.users.get_by_email(email)
        valid = verify_password(password, user.hashed_password if user else None)
        if not user or not valid or not user.is_active:
            raise AuthenticationError("Incorrect email or password")
        self.tokens.delete_expired()
        raw, row = self._new_refresh_token(user)
        self.tokens.add(row)
        return self._pair(user, raw)

    def refresh(self, raw_token: str) -> TokenPair:
        """Exchange a valid refresh token for a new access token AND a new refresh token."""
        stored = self.tokens.get_by_hash(hash_refresh_token(raw_token))
        if stored is None:
            raise AuthenticationError("Invalid refresh token")

        now = utc_now()
        if stored.revoked_at is not None:
            if now - _aware(stored.revoked_at) > REUSE_GRACE:
                self.tokens.revoke_all_for_user(stored.user_id)  # reuse detected
            raise AuthenticationError("Refresh token is no longer valid")
        if _aware(stored.expires_at) <= now:
            raise AuthenticationError("Refresh token expired")

        user = self.users.get(stored.user_id)
        if user is None or not user.is_active:
            self.tokens.revoke_all_for_user(stored.user_id)
            raise AuthenticationError("Account is not active")

        raw, row = self._new_refresh_token(user)
        self.tokens.rotate(stored, row)
        return self._pair(user, raw)

    def logout(self, raw_token: str | None) -> None:
        """Revoke this session's refresh token. Always succeeds (idempotent)."""
        if not raw_token:
            return
        stored = self.tokens.get_by_hash(hash_refresh_token(raw_token))
        if stored is not None and stored.revoked_at is None:
            self.tokens.revoke(stored)

    # ---- helpers ----

    def _new_refresh_token(self, user: User) -> tuple[str, RefreshToken]:
        raw, token_hash = generate_refresh_token()
        row = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return raw, row

    def _pair(self, user: User, raw_refresh: str) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=raw_refresh,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
