from fastapi import APIRouter, Query, status

from dependencies import CurrentUser, TransactionSvc
from schemas import TransactionCreate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(data: TransactionCreate, current_user: CurrentUser, service: TransactionSvc):
    return service.create(current_user.id, data)


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    current_user: CurrentUser,
    service: TransactionSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
):
    """Newest first."""
    return service.list(current_user.id, skip=skip, limit=limit)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, current_user: CurrentUser, service: TransactionSvc):
    service.delete(transaction_id, current_user.id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_transactions(current_user: CurrentUser, service: TransactionSvc):
    """Delete all of the current user's transactions."""
    service.clear(current_user.id)
