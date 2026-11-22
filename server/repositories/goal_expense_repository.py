from typing import Sequence

from entities.goal_expense import GoalExpense
from repositories.base import BaseRepository


class GoalExpenseRepository(BaseRepository[GoalExpense]):
    model = GoalExpense

    def get_for_goal(self, expense_id: int, goal_id: int, user_id: int) -> GoalExpense | None:
        return self.first(id=expense_id, goal_id=goal_id, user_id=user_id)

    def list_for_user(self, user_id: int) -> Sequence[GoalExpense]:
        """Dated expenses in date order; undated ones last."""
        return self.list(
            limit=10000,
            order_by=(GoalExpense.planned_date.asc().nulls_last(), GoalExpense.id.asc()),
            user_id=user_id,
        )
