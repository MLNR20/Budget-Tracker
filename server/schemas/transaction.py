from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from entities.transaction import TransactionType


class TransactionCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    type: TransactionType
    category: str = Field(min_length=1, max_length=50)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    description: str
    amount: Decimal
    type: TransactionType
    category: str
    date_created: datetime
    date_updated: datetime
    is_active: bool
