from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from entities.recurring_transaction import Frequency
from entities.transaction import TransactionType


class RecurringCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    type: TransactionType
    category: str = Field(min_length=1, max_length=50)
    frequency: Frequency
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def _end_not_before_start(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date can't be before start_date")
        return self


class RecurringUpdate(BaseModel):
    """Frequency and start date are fixed once created (delete and recreate to change them)."""

    description: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    type: TransactionType | None = None
    category: str | None = Field(default=None, min_length=1, max_length=50)
    end_date: date | None = None  # send null to remove the end date
    is_active: bool | None = None  # false = pause, true = resume


class RecurringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    description: str
    amount: Decimal
    type: TransactionType
    category: str
    frequency: Frequency
    start_date: date
    end_date: date | None
    next_run_date: date
    occurrences_generated: int
    is_active: bool
    date_created: datetime
    date_updated: datetime


class ProcessResult(BaseModel):
    created: int
