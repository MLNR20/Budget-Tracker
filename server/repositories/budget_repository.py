from typing import Sequence

from entities.budget import Budget
from repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    model = Budget

    def get_for_user(self, budget_id: int, user_id: int) -> Budget | None:
        return self.first(id=budget_id, user_id=user_id)

    def list_for_user(self, user_id: int, skip: int = 0, limit: int = 100) -> Sequence[Budget]:
        return self.list(skip=skip, limit=limit, user_id=user_id)
