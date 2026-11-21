from typing import Sequence

from entities.budget import Budget
from repositories import BudgetRepository, CardRepository
from schemas import BudgetCreate, BudgetUpdate
from services.exceptions import BusinessRuleError, NotFoundError


class BudgetService:
    def __init__(self, budgets: BudgetRepository, cards: CardRepository):
        self.budgets = budgets
        self.cards = cards

    def get(self, budget_id: int, user_id: int) -> Budget:
        budget = self.budgets.get_for_user(budget_id, user_id)
        if budget is None:
            raise NotFoundError("Budget not found")
        return budget

    def list(self, user_id: int, skip: int = 0, limit: int = 100) -> Sequence[Budget]:
        return self.budgets.list_for_user(user_id, skip=skip, limit=limit)

    def create(self, user_id: int, data: BudgetCreate) -> Budget:
        return self.budgets.add(Budget(user_id=user_id, **data.model_dump()))

    def update(self, budget_id: int, user_id: int, data: BudgetUpdate) -> Budget:
        budget = self.get(budget_id, user_id)
        values = data.model_dump(exclude_unset=True, exclude_none=True)
        if "current_amount" in values:
            allocated = self.cards.allocated_total(budget.id)
            if values["current_amount"] < allocated:
                raise BusinessRuleError(
                    f"Budget can't drop below the {allocated} already split into cards"
                )
        return self.budgets.update(budget, values)

    def delete(self, budget_id: int, user_id: int) -> None:
        """Hard delete; the budget's cards are removed with it."""
        self.budgets.delete(self.get(budget_id, user_id))
