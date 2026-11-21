from typing import Sequence

from sqlalchemy import delete, select

from entities.transaction import Transaction, TransactionType
from repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction

    def get_for_user(self, transaction_id: int, user_id: int) -> Transaction | None:
        return self.first(id=transaction_id, user_id=user_id)

    def list_for_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[Transaction]:
        """Newest first."""
        return self.list(
            skip=skip,
            limit=limit,
            order_by=(Transaction.date_created.desc(), Transaction.id.desc()),
            user_id=user_id,
        )

    def list_for_analytics(
        self,
        user_id: int,
        type: TransactionType | None = None,
        category: str | None = None,
    ) -> Sequence[Transaction]:
        """All of a user's transactions, optionally narrowed by type/category (oldest first).

        Date filtering and grouping are done by the analytics service in Python so the result is
        identical on SQLite and PostgreSQL (they handle timezone-aware datetimes differently).
        """
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        if type is not None:
            stmt = stmt.where(Transaction.type == type)
        if category is not None:
            stmt = stmt.where(Transaction.category == category)
        stmt = stmt.order_by(Transaction.date_created.asc(), Transaction.id.asc())
        return self.session.scalars(stmt).all()

    def categories_for_user(self, user_id: int) -> list[str]:
        stmt = (
            select(Transaction.category)
            .where(Transaction.user_id == user_id)
            .distinct()
            .order_by(Transaction.category)
        )
        return list(self.session.scalars(stmt).all())

    def delete_all_for_user(self, user_id: int) -> None:
        self.session.execute(delete(Transaction).where(Transaction.user_id == user_id))
        self.session.commit()
