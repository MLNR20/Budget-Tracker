from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from entities.base_entity import BaseEntity


class Goal(BaseEntity):
    """Something to save for (a trip, a laptop, an emergency fund) with a target and a deadline."""

    __tablename__ = "goals"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Free-text plan: how you intend to reach the goal.
    plan: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_achieved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
