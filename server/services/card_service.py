from decimal import Decimal
from typing import Sequence

from entities.budget import Budget
from entities.card import Card
from repositories import BudgetRepository, CardRepository
from schemas import CardCreate, CardUpdate
from services.exceptions import BusinessRuleError, NotFoundError


class CardService:
    """Splits a budget into cards. The cards of a budget can't add up to more than it holds."""

    def __init__(self, cards: CardRepository, budgets: BudgetRepository):
        self.cards = cards
        self.budgets = budgets

    def get(self, card_id: int, user_id: int) -> Card:
        card = self.cards.get_for_user(card_id, user_id)
        if card is None:
            raise NotFoundError("Card not found")
        return card

    def list(
        self, user_id: int, budget_id: int | None = None, skip: int = 0, limit: int = 100
    ) -> Sequence[Card]:
        return self.cards.list_for_user(user_id, budget_id=budget_id, skip=skip, limit=limit)

    def create(self, user_id: int, data: CardCreate) -> Card:
        budget = self.budgets.get_for_user(data.budget_id, user_id)
        if budget is None:
            raise NotFoundError("Budget not found")
        self._ensure_fits(budget, data.amount)
        return self.cards.add(Card(user_id=user_id, **data.model_dump()))

    def update(self, card_id: int, user_id: int, data: CardUpdate) -> Card:
        card = self.get(card_id, user_id)
        values = data.model_dump(exclude_unset=True, exclude_none=True)
        if "amount" in values:
            budget = self.budgets.get(card.budget_id)
            self._ensure_fits(budget, values["amount"], exclude_card_id=card.id)
        return self.cards.update(card, values)

    def delete(self, card_id: int, user_id: int) -> None:
        """Deleting a card frees its amount back to the budget."""
        self.cards.delete(self.get(card_id, user_id))

    def _ensure_fits(
        self, budget: Budget, amount: Decimal, exclude_card_id: int | None = None
    ) -> None:
        allocated = self.cards.allocated_total(budget.id, exclude_card_id)
        if allocated + amount > budget.current_amount:
            remaining = budget.current_amount - allocated
            raise BusinessRuleError(
                f"Not enough left in budget to split: {remaining} available, {amount} requested"
            )
