from typing import Sequence

from entities.transaction import Transaction
from repositories import TransactionRepository
from schemas import TransactionCreate
from services.exceptions import NotFoundError


class TransactionService:
    def __init__(self, transactions: TransactionRepository):
        self.transactions = transactions

    def list(self, user_id: int, skip: int = 0, limit: int = 100) -> Sequence[Transaction]:
        return self.transactions.list_for_user(user_id, skip=skip, limit=limit)

    def create(self, user_id: int, data: TransactionCreate) -> Transaction:
        return self.transactions.add(Transaction(user_id=user_id, **data.model_dump()))

    def delete(self, transaction_id: int, user_id: int) -> None:
        transaction = self.transactions.get_for_user(transaction_id, user_id)
        if transaction is None:
            raise NotFoundError("Transaction not found")
        self.transactions.delete(transaction)

    def clear(self, user_id: int) -> None:
        self.transactions.delete_all_for_user(user_id)
