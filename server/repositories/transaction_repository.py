from typing import Sequence

from sqlalchemy import delete

from entities.transaction import Transaction
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

    def delete_all_for_user(self, user_id: int) -> None:
        self.session.execute(delete(Transaction).where(Transaction.user_id == user_id))
        self.session.commit()
