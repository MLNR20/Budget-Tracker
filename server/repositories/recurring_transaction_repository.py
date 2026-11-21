from datetime import date
from typing import Iterable, Sequence

from sqlalchemy import select

from entities.recurring_transaction import RecurringTransaction
from entities.transaction import Transaction
from repositories.base import BaseRepository


class RecurringTransactionRepository(BaseRepository[RecurringTransaction]):
    model = RecurringTransaction

    def get_for_user(self, rule_id: int, user_id: int) -> RecurringTransaction | None:
        return self.first(id=rule_id, user_id=user_id)

    def list_for_user(self, user_id: int) -> Sequence[RecurringTransaction]:
        return self.list(
            limit=500,
            order_by=(RecurringTransaction.next_run_date.asc(), RecurringTransaction.id.asc()),
            user_id=user_id,
        )

    def lock_due(self, user_id: int, today: date) -> Sequence[RecurringTransaction]:
        """Active rules that are due, locked for the rest of the transaction.

        skip_locked: if another request (say login and the dashboard at the same moment) is
        already handling a rule, this one skips it instead of creating the same transactions
        twice. SQLite has no row locks and simply ignores the clause.
        """
        stmt = (
            select(RecurringTransaction)
            .where(
                RecurringTransaction.user_id == user_id,
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.next_run_date <= today,
            )
            .with_for_update(skip_locked=True)
        )
        return self.session.scalars(stmt).all()

    def save_generated(self, new_transactions: Iterable[Transaction]) -> None:
        """Insert the generated transactions and commit, together with the already-modified
        rules (new next_run_date / count), in ONE transaction. They succeed or fail together,
        which is what keeps catch-up from ever creating duplicates."""
        self.session.add_all(list(new_transactions))
        self.session.commit()
