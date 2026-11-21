import enum
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from entities.base_entity import BaseEntity


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class Transaction(BaseEntity):
    """A single income or expense. `date_created` is the transaction date."""

    __tablename__ = "transactions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, length=10), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
