from fastapi import APIRouter, Query, status

from dependencies import CardSvc, CurrentUser
from schemas import CardCreate, CardResponse, CardUpdate

router = APIRouter(prefix="/cards", tags=["cards"])


@router.post("", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def create_card(data: CardCreate, current_user: CurrentUser, service: CardSvc):
    """Split part of a budget into a new card."""
    return service.create(current_user.id, data)


@router.get("", response_model=list[CardResponse])
def list_cards(
    current_user: CurrentUser,
    service: CardSvc,
    budget_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    return service.list(current_user.id, budget_id=budget_id, skip=skip, limit=limit)


@router.get("/{card_id}", response_model=CardResponse)
def read_card(card_id: int, current_user: CurrentUser, service: CardSvc):
    return service.get(card_id, current_user.id)


@router.patch("/{card_id}", response_model=CardResponse)
def update_card(card_id: int, data: CardUpdate, current_user: CurrentUser, service: CardSvc):
    return service.update(card_id, current_user.id, data)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, current_user: CurrentUser, service: CardSvc):
    """Deleting a card frees its amount back to the budget."""
    service.delete(card_id, current_user.id)
