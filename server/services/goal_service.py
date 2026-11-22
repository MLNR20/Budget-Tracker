import math
from datetime import date
from decimal import Decimal
from typing import Sequence

from entities.budget import Budget
from entities.goal import Goal
from entities.goal_budget import GoalBudget
from entities.goal_expense import GoalExpense
from repositories import (
    BudgetRepository,
    GoalBudgetRepository,
    GoalExpenseRepository,
    GoalRepository,
)
from schemas.budget import BudgetResponse
from schemas.goal import (
    GoalCreate,
    GoalDetail,
    GoalExpenseCreate,
    GoalExpenseResponse,
    GoalExpenseUpdate,
    GoalResponse,
    GoalSummary,
    GoalUpdate,
)
from services.clock import local_today
from services.exceptions import BusinessRuleError, NotFoundError

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
DAYS_PER_MONTH = 30.44
# GoalResponse fields that are computed, not read straight off the Goal row.
_COMPUTED = {"summary", "budget_ids"}


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT)


def build_summary(
    goal: Goal, budgets: Sequence[Budget], expenses: Sequence[GoalExpense], today: date
) -> GoalSummary:
    """Pure calculation (no database): the goal's progress and savings plan."""
    funded = sum((b.current_amount for b in budgets), ZERO)
    planned = sum((e.amount for e in expenses), ZERO)
    paid = sum((e.amount for e in expenses if e.is_paid), ZERO)
    remaining = max(ZERO, goal.target_amount - funded)
    progress = float(min(Decimal(100), funded / goal.target_amount * 100)) if goal.target_amount > 0 else 0.0

    days_left = (goal.target_date - today).days if goal.target_date else None
    overdue = bool(days_left is not None and days_left < 0 and not goal.is_achieved and remaining > 0)

    monthly = None
    if days_left is not None and days_left > 0 and remaining > 0 and not goal.is_achieved:
        months_left = max(1, math.ceil(days_left / DAYS_PER_MONTH))
        monthly = _money(remaining / months_left)

    return GoalSummary(
        funded_amount=_money(funded),
        remaining_to_fund=_money(remaining),
        progress_pct=round(progress, 1),
        planned_total=_money(planned),
        paid_total=_money(paid),
        unpaid_total=_money(planned - paid),
        unplanned_amount=_money(goal.target_amount - planned),
        days_left=days_left,
        is_overdue=overdue,
        monthly_needed=monthly,
    )


class GoalService:
    """Goals you save for: budgets assigned to them, an expense list, dates and a savings plan."""

    def __init__(
        self,
        goals: GoalRepository,
        links: GoalBudgetRepository,
        expenses: GoalExpenseRepository,
        budgets: BudgetRepository,
    ):
        self.goals = goals
        self.links = links
        self.expenses = expenses
        self.budgets = budgets

    # ---- goals ----

    def list(self, user_id: int) -> list[GoalResponse]:
        goals = self.goals.list_for_user(user_id)
        budgets_by_id = {b.id: b for b in self.budgets.list_for_user(user_id, limit=5000)}
        links = self.links.list_for_user(user_id)
        expenses = self.expenses.list_for_user(user_id)
        today = local_today()
        return [
            self._response(
                g,
                [budgets_by_id[l.budget_id] for l in links if l.goal_id == g.id and l.budget_id in budgets_by_id],
                [e for e in expenses if e.goal_id == g.id],
                today,
            )
            for g in goals
        ]

    def get(self, goal_id: int, user_id: int) -> GoalDetail:
        return self._detail(self._goal(goal_id, user_id), user_id)

    def create(self, user_id: int, data: GoalCreate) -> GoalDetail:
        goal = self.goals.add(Goal(user_id=user_id, **data.model_dump()))
        return self._detail(goal, user_id)

    def update(self, goal_id: int, user_id: int, data: GoalUpdate) -> GoalDetail:
        goal = self._goal(goal_id, user_id)
        # target_date and plan may be sent as null to clear them; the rest must not be null.
        values = {
            k: v
            for k, v in data.model_dump(exclude_unset=True).items()
            if v is not None or k in ("target_date", "plan")
        }
        new_target = values.get("target_date")
        if new_target is not None:
            if new_target < goal.start_date:
                raise BusinessRuleError("The target date can't be before the start date.")
            late = [
                e for e in self.expenses.list_for_user(user_id)
                if e.goal_id == goal.id and e.planned_date and e.planned_date > new_target
            ]
            if late:
                raise BusinessRuleError(
                    f"{len(late)} planned expense(s) are dated after that target date. "
                    "Move or delete them first."
                )
        self.goals.update(goal, values)
        return self._detail(goal, user_id)

    def delete(self, goal_id: int, user_id: int) -> None:
        """Deletes the goal, its expense list and its budget assignments. The budgets stay."""
        self.goals.delete(self._goal(goal_id, user_id))

    # ---- budgets assigned to a goal ----

    def assign_budget(self, goal_id: int, user_id: int, budget_id: int) -> GoalDetail:
        goal = self._goal(goal_id, user_id)
        if self.budgets.get_for_user(budget_id, user_id) is None:
            raise NotFoundError("Budget not found")
        existing = self.links.get_by_budget(budget_id)
        if existing is not None and existing.goal_id == goal.id:
            return self._detail(goal, user_id)  # already assigned: nothing to do
        if existing is not None:
            other = self.goals.get(existing.goal_id)
            raise BusinessRuleError(
                f'That budget already funds the goal "{other.name if other else "another goal"}". '
                "Remove it from there first."
            )
        self.links.add(GoalBudget(user_id=user_id, goal_id=goal.id, budget_id=budget_id))
        return self._detail(goal, user_id)

    def unassign_budget(self, goal_id: int, user_id: int, budget_id: int) -> GoalDetail:
        goal = self._goal(goal_id, user_id)
        link = self.links.get_link(goal.id, budget_id, user_id)
        if link is None:
            raise NotFoundError("That budget isn't assigned to this goal")
        self.links.delete(link)
        return self._detail(goal, user_id)

    # ---- expense list ----

    def add_expense(self, goal_id: int, user_id: int, data: GoalExpenseCreate) -> GoalDetail:
        goal = self._goal(goal_id, user_id)
        self._check_date_in_range(goal, data.planned_date)
        self.expenses.add(GoalExpense(user_id=user_id, goal_id=goal.id, **data.model_dump()))
        return self._detail(goal, user_id)

    def update_expense(
        self, goal_id: int, expense_id: int, user_id: int, data: GoalExpenseUpdate
    ) -> GoalDetail:
        goal = self._goal(goal_id, user_id)
        expense = self.expenses.get_for_goal(expense_id, goal.id, user_id)
        if expense is None:
            raise NotFoundError("Expense not found")
        values = {
            k: v
            for k, v in data.model_dump(exclude_unset=True).items()
            if v is not None or k in ("planned_date", "notes")
        }
        if "planned_date" in values:
            self._check_date_in_range(goal, values["planned_date"])
        self.expenses.update(expense, values)
        return self._detail(goal, user_id)

    def delete_expense(self, goal_id: int, expense_id: int, user_id: int) -> GoalDetail:
        goal = self._goal(goal_id, user_id)
        expense = self.expenses.get_for_goal(expense_id, goal.id, user_id)
        if expense is None:
            raise NotFoundError("Expense not found")
        self.expenses.delete(expense)
        return self._detail(goal, user_id)

    # ---- helpers ----

    def _goal(self, goal_id: int, user_id: int) -> Goal:
        goal = self.goals.get_for_user(goal_id, user_id)
        if goal is None:
            raise NotFoundError("Goal not found")
        return goal

    @staticmethod
    def _check_date_in_range(goal: Goal, planned: date | None) -> None:
        if planned is not None and goal.target_date is not None and planned > goal.target_date:
            raise BusinessRuleError("An expense can't be planned after the goal's target date.")

    @staticmethod
    def _response(goal: Goal, budgets: Sequence[Budget], expenses: Sequence[GoalExpense], today: date) -> GoalResponse:
        return GoalResponse.model_validate(
            {
                **{c: getattr(goal, c) for c in GoalResponse.model_fields if c not in _COMPUTED},
                "budget_ids": [b.id for b in budgets],
                "summary": build_summary(goal, budgets, expenses, today),
            }
        )

    def _detail(self, goal: Goal, user_id: int) -> GoalDetail:
        links = [l for l in self.links.list_for_user(user_id) if l.goal_id == goal.id]
        budgets_by_id = {b.id: b for b in self.budgets.list_for_user(user_id, limit=5000)}
        budgets = [budgets_by_id[l.budget_id] for l in links if l.budget_id in budgets_by_id]
        expenses = [e for e in self.expenses.list_for_user(user_id) if e.goal_id == goal.id]
        summary = build_summary(goal, budgets, expenses, local_today())
        return GoalDetail.model_validate(
            {
                **{c: getattr(goal, c) for c in GoalResponse.model_fields if c not in _COMPUTED},
                "budget_ids": [b.id for b in budgets],
                "summary": summary,
                "budgets": [BudgetResponse.model_validate(b) for b in budgets],
                "expenses": [GoalExpenseResponse.model_validate(e) for e in expenses],
            }
        )
