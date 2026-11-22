from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from entities.base_entity import BaseEntity


class GoalBudget(BaseEntity):
    """Assigns a budget to a goal. A goal can have many budgets; a budget funds at most one goal
    (budget_id is unique). A separate link table, rather than a column on `budgets`, so existing
    databases only gain a table and the budgets table is left untouched."""

    __tablename__ = "goal_budgets"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
