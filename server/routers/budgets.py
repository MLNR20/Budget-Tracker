from fastapi import APIRouter, Query, status

from dependencies import BudgetSvc, CurrentUser
from schemas import BudgetCreate, BudgetResponse, BudgetUpdate

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(data: BudgetCreate, current_user: CurrentUser, service: BudgetSvc):
    return service.create(current_user.id, data)


@router.get("", response_model=list[BudgetResponse])
def list_budgets(
    current_user: CurrentUser,
    service: BudgetSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    return service.list(current_user.id, skip=skip, limit=limit)


@router.get("/{budget_id}", response_model=BudgetResponse)
def read_budget(budget_id: int, current_user: CurrentUser, service: BudgetSvc):
    return service.get(budget_id, current_user.id)


@router.patch("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int, data: BudgetUpdate, current_user: CurrentUser, service: BudgetSvc
):
    return service.update(budget_id, current_user.id, data)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: int, current_user: CurrentUser, service: BudgetSvc):
    """Hard delete. The budget's cards are deleted with it."""
    service.delete(budget_id, current_user.id)
