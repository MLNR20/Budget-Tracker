from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from entities.base_entity import BaseEntity


class Card(BaseEntity):
    """A slice of a budget. A budget is split across cards, each holding part of its amount."""

    __tablename__ = "cards"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Bootstrap Icons name without the "bi-" prefix, e.g. "cart" or "house".
    icon: Mapped[str] = mapped_column(String(50), default="wallet2", nullable=False)
    # Portion of the budget's current_amount assigned to this card.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
