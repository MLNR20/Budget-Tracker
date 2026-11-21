from sqlalchemy import delete, update

from entities.base_entity import utc_now
from entities.refresh_token import RefreshToken
from repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.first(token_hash=token_hash)

    def rotate(self, old: RefreshToken, new: RefreshToken) -> RefreshToken:
        """Revoke the used token and store its replacement in one transaction."""
        old.revoked_at = utc_now()
        self.session.add(new)
        self.session.commit()
        self.session.refresh(new)
        return new

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = utc_now()
        self.session.commit()

    def revoke_all_for_user(self, user_id: int) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        self.session.commit()

    def delete_expired(self) -> None:
        """Housekeeping: expired rows can never be used again."""
        # synchronize_session=False: compare in the database, not in Python against loaded rows
        # (SQLite returns naive datetimes, which can't be compared with an aware one).
        self.session.execute(
            delete(RefreshToken)
            .where(RefreshToken.expires_at < utc_now())
            .execution_options(synchronize_session=False)
        )
        self.session.commit()
