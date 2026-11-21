import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from entities.base_entity import BaseEntity
from entities.transaction import TransactionType


class Frequency(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class RecurringTransaction(BaseEntity):
    """A rule that creates a real Transaction every period (e.g. rent on the 1st of each month).

    `is_active` doubles as pause/resume, and is switched off when the rule passes its end date.
    """

    __tablename__ = "recurring_transactions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, length=10), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[Frequency] = mapped_column(
        Enum(Frequency, native_enum=False, length=10), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # The next date a transaction is due. Catch-up creates one for every date up to today.
    next_run_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    # How many have been created so far. Dates are computed from start_date + this count (not by
    # repeatedly adding to the previous date), so "monthly from the 31st" never drifts to the 28th.
    occurrences_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
