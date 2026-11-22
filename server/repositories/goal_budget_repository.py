from typing import Sequence

from entities.goal_budget import GoalBudget
from repositories.base import BaseRepository


class GoalBudgetRepository(BaseRepository[GoalBudget]):
    model = GoalBudget

    def get_by_budget(self, budget_id: int) -> GoalBudget | None:
        return self.first(budget_id=budget_id)

    def get_link(self, goal_id: int, budget_id: int, user_id: int) -> GoalBudget | None:
        return self.first(goal_id=goal_id, budget_id=budget_id, user_id=user_id)

    def list_for_user(self, user_id: int) -> Sequence[GoalBudget]:
        return self.list(limit=5000, user_id=user_id)
