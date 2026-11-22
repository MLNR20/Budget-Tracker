from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.budget import BudgetResponse


# ---- goals ----

class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    start_date: date
    target_date: date | None = None
    plan: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _target_not_before_start(self):
        if self.target_date is not None and self.target_date < self.start_date:
            raise ValueError("target_date can't be before start_date")
        return self


class GoalUpdate(BaseModel):
    """The start date is fixed once created."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    target_date: date | None = None  # send null to remove the deadline
    plan: str | None = Field(default=None, max_length=2000)  # send null to clear it
    is_achieved: bool | None = None


class GoalSummary(BaseModel):
    """Numbers computed from the goal, its assigned budgets and its expense list."""

    funded_amount: Decimal  # sum of the assigned budgets' current amounts
    remaining_to_fund: Decimal  # target - funded, never below 0
    progress_pct: float  # funded / target, 0-100
    planned_total: Decimal  # sum of the expense list
    paid_total: Decimal
    unpaid_total: Decimal
    unplanned_amount: Decimal  # target - planned_total (negative: the plan costs more than the target)
    days_left: int | None  # until the target date (negative once it has passed)
    is_overdue: bool  # deadline passed, goal not achieved and not fully funded
    monthly_needed: Decimal | None  # remaining_to_fund spread over the months left


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    target_amount: Decimal
    start_date: date
    target_date: date | None
    plan: str | None
    is_achieved: bool
    date_created: datetime
    date_updated: datetime
    budget_ids: list[int]  # ids of the budgets assigned to this goal
    summary: GoalSummary


# ---- expense list ----

class GoalExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    planned_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)


class GoalExpenseUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    planned_date: date | None = None  # send null to remove the date
    notes: str | None = Field(default=None, max_length=500)  # send null to clear
    is_paid: bool | None = None


class GoalExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goal_id: int
    description: str
    amount: Decimal
    planned_date: date | None
    notes: str | None
    is_paid: bool
    date_created: datetime
    date_updated: datetime


# ---- assigning budgets ----

class AssignBudget(BaseModel):
    budget_id: int


class GoalDetail(GoalResponse):
    budgets: list[BudgetResponse]  # budgets assigned to this goal
    expenses: list[GoalExpenseResponse]  # dated ones in date order, undated last
