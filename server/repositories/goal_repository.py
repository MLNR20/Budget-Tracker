from typing import Sequence

from entities.goal import Goal
from repositories.base import BaseRepository


class GoalRepository(BaseRepository[Goal]):
    model = Goal

    def get_for_user(self, goal_id: int, user_id: int) -> Goal | None:
        return self.first(id=goal_id, user_id=user_id)

    def list_for_user(self, user_id: int) -> Sequence[Goal]:
        """Open goals first, soonest deadline first (goals without a deadline last)."""
        return self.list(
            limit=500,
            order_by=(Goal.is_achieved.asc(), Goal.target_date.asc().nulls_last(), Goal.id.asc()),
            user_id=user_id,
        )
