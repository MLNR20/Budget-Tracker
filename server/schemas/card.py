from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

ICON_PATTERN = r"^[a-z0-9-]{1,50}$"


class CardCreate(BaseModel):
    budget_id: int
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    icon: str = Field(default="wallet2", pattern=ICON_PATTERN)


class CardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    icon: str | None = Field(default=None, pattern=ICON_PATTERN)


class CardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    budget_id: int
    name: str
    amount: Decimal
    icon: str
    date_created: datetime
    date_updated: datetime
    is_active: bool
