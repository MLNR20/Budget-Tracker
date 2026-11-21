from sqlalchemy import delete, select, update

from entities.base_entity import utc_now
from entities.password_reset_token import PasswordResetToken
from repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self.first(token_hash=token_hash)

    def latest_for_user(self, user_id: int) -> PasswordResetToken | None:
        stmt = (
            select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id)
            .order_by(PasswordResetToken.date_created.desc(), PasswordResetToken.id.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def mark_all_used_for_user(self, user_id: int) -> None:
        """Invalidate every outstanding reset link for the user."""
        self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=utc_now())
        )
        self.session.commit()

    def delete_expired(self) -> None:
        # synchronize_session=False: let the database do the comparison. The default would
        # re-evaluate it in Python against already-loaded rows, and SQLite hands those back
        # timezone-naive, which can't be compared with an aware datetime.
        self.session.execute(
            delete(PasswordResetToken)
            .where(PasswordResetToken.expires_at < utc_now())
            .execution_options(synchronize_session=False)
        )
        self.session.commit()
