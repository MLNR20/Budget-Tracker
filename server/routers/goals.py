from fastapi import APIRouter, status

from dependencies import CurrentUser, GoalSvc
from schemas.goal import (
    AssignBudget,
    GoalCreate,
    GoalDetail,
    GoalExpenseCreate,
    GoalExpenseUpdate,
    GoalResponse,
    GoalUpdate,
)

router = APIRouter(prefix="/goals", tags=["goals"])


# ---- goals ----

@router.post("", response_model=GoalDetail, status_code=status.HTTP_201_CREATED)
def create_goal(data: GoalCreate, current_user: CurrentUser, service: GoalSvc):
    return service.create(current_user.id, data)


@router.get("", response_model=list[GoalResponse])
def list_goals(current_user: CurrentUser, service: GoalSvc):
    """All goals with their progress summary. Open goals first, soonest deadline first."""
    return service.list(current_user.id)


@router.get("/{goal_id}", response_model=GoalDetail)
def read_goal(goal_id: int, current_user: CurrentUser, service: GoalSvc):
    """One goal with its assigned budgets, expense list and savings plan."""
    return service.get(goal_id, current_user.id)


@router.patch("/{goal_id}", response_model=GoalDetail)
def update_goal(goal_id: int, data: GoalUpdate, current_user: CurrentUser, service: GoalSvc):
    return service.update(goal_id, current_user.id, data)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, current_user: CurrentUser, service: GoalSvc):
    """Deletes the goal, its expense list and its assignments. The budgets themselves stay."""
    service.delete(goal_id, current_user.id)


# ---- budgets assigned to a goal ----

@router.post("/{goal_id}/budgets", response_model=GoalDetail)
def assign_budget(goal_id: int, data: AssignBudget, current_user: CurrentUser, service: GoalSvc):
    """Assign one of your budgets to this goal. A budget can fund only one goal."""
    return service.assign_budget(goal_id, current_user.id, data.budget_id)


@router.delete("/{goal_id}/budgets/{budget_id}", response_model=GoalDetail)
def unassign_budget(goal_id: int, budget_id: int, current_user: CurrentUser, service: GoalSvc):
    return service.unassign_budget(goal_id, current_user.id, budget_id)


# ---- the goal's expense list ----

@router.post("/{goal_id}/expenses", response_model=GoalDetail, status_code=status.HTTP_201_CREATED)
def add_expense(goal_id: int, data: GoalExpenseCreate, current_user: CurrentUser, service: GoalSvc):
    return service.add_expense(goal_id, current_user.id, data)


@router.patch("/{goal_id}/expenses/{expense_id}", response_model=GoalDetail)
def update_expense(
    goal_id: int, expense_id: int, data: GoalExpenseUpdate, current_user: CurrentUser, service: GoalSvc
):
    return service.update_expense(goal_id, expense_id, current_user.id, data)


@router.delete("/{goal_id}/expenses/{expense_id}", response_model=GoalDetail)
def delete_expense(goal_id: int, expense_id: int, current_user: CurrentUser, service: GoalSvc):
    return service.delete_expense(goal_id, expense_id, current_user.id)
