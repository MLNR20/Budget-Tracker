from decimal import Decimal
from typing import Sequence

from entities.card import Card
from repositories.base import BaseRepository


class CardRepository(BaseRepository[Card]):
    model = Card

    def get_for_user(self, card_id: int, user_id: int) -> Card | None:
        return self.first(id=card_id, user_id=user_id)

    def list_for_user(
        self, user_id: int, budget_id: int | None = None, skip: int = 0, limit: int = 100
    ) -> Sequence[Card]:
        filters = {"user_id": user_id}
        if budget_id is not None:
            filters["budget_id"] = budget_id
        return self.list(skip=skip, limit=limit, **filters)

    def allocated_total(self, budget_id: int, exclude_card_id: int | None = None) -> Decimal:
        """Sum of card amounts already split out of a budget."""
        cards = self.list(limit=10_000, budget_id=budget_id)
        return sum(
            (c.amount for c in cards if c.id != exclude_card_id), start=Decimal("0.00")
        )
