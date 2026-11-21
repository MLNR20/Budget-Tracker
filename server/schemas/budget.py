from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BudgetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    current_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)


class BudgetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    current_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    current_amount: Decimal
    date_created: datetime
    date_updated: datetime
    is_active: bool
