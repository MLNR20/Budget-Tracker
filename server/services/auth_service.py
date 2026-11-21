from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    FRONTEND_URL,
    PASSWORD_RESET_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from entities.base_entity import utc_now
from entities.password_reset_token import PasswordResetToken
from entities.refresh_token import RefreshToken
from entities.user import User
from repositories import PasswordResetTokenRepository, RefreshTokenRepository, UserRepository
from security import (
    create_access_token,
    generate_refresh_token,
    generate_token,
    hash_password,
    hash_refresh_token,
    hash_token,
    verify_password,
)
from services.email_service import send_password_reset_email
from services.exceptions import AuthenticationError, BusinessRuleError

# Two requests can race with the same refresh token (e.g. two tabs). A token rotated this recently
# is simply rejected; replaying one rotated longer ago is treated as theft and kills all sessions.
REUSE_GRACE = timedelta(seconds=10)

# At most one reset email per account in this window, so the form can't be used to spam someone.
RESET_REQUEST_COOLDOWN = timedelta(seconds=60)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str  # raw value, for the cookie only; never stored
    expires_in: int  # access token lifetime in seconds


def _aware(value: datetime) -> datetime:
    # SQLite returns naive datetimes; everything here is UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        tokens: RefreshTokenRepository,
        reset_tokens: PasswordResetTokenRepository,
    ):
        self.users = users
        self.tokens = tokens
        self.reset_tokens = reset_tokens

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

    # ---- forgot / reset password ----

    def request_password_reset(self, email: str) -> None:
        """Email a reset link if the account exists. Silent either way.

        The caller must not let the outcome (or its timing) reach the client, otherwise this
        endpoint would reveal which emails have accounts; routers run it as a background task.
        """
        user = self.users.get_by_email(email)
        if user is None or not user.is_active:
            return

        recent = self.reset_tokens.latest_for_user(user.id)
        if recent is not None and utc_now() - _aware(recent.date_created) < RESET_REQUEST_COOLDOWN:
            return

        self.reset_tokens.delete_expired()
        self.reset_tokens.mark_all_used_for_user(user.id)  # only the newest link works
        raw, token_hash = generate_token()
        self.reset_tokens.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=utc_now() + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES),
            )
        )
        # The token goes in the URL fragment (#...), which browsers never send to any server,
        # so it can't end up in access logs or Referer headers.
        send_password_reset_email(user.email, f"{FRONTEND_URL}/#reset-password={raw}")

    def reset_password(self, raw_token: str, new_password: str) -> None:
        stored = self.reset_tokens.get_by_hash(hash_token(raw_token))
        invalid = BusinessRuleError("This reset link is invalid or has expired.")
        if stored is None or stored.used_at is not None or _aware(stored.expires_at) <= utc_now():
            raise invalid
        user = self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise invalid

        self.users.update(user, {"hashed_password": hash_password(new_password)})
        self.reset_tokens.mark_all_used_for_user(user.id)
        # A password reset means "sign out everywhere": kill every refresh token.
        self.tokens.revoke_all_for_user(user.id)

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
