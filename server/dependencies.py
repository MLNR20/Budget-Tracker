from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from entities.user import User
from repositories.budget_repository import BudgetRepository
from repositories.card_repository import CardRepository
from repositories.transaction_repository import TransactionRepository
from repositories.user_repository import UserRepository
from security import decode_access_token
from services import BudgetService, CardService, TransactionService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_budget_repository(db: DbSession) -> BudgetRepository:
    return BudgetRepository(db)


def get_card_repository(db: DbSession) -> CardRepository:
    return CardRepository(db)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
BudgetRepo = Annotated[BudgetRepository, Depends(get_budget_repository)]
CardRepo = Annotated[CardRepository, Depends(get_card_repository)]


def get_transaction_repository(db: DbSession) -> TransactionRepository:
    return TransactionRepository(db)


TransactionRepo = Annotated[TransactionRepository, Depends(get_transaction_repository)]


def get_transaction_service(transactions: TransactionRepo) -> TransactionService:
    return TransactionService(transactions)


TransactionSvc = Annotated[TransactionService, Depends(get_transaction_service)]


def get_budget_service(budgets: BudgetRepo, cards: CardRepo) -> BudgetService:
    return BudgetService(budgets, cards)


def get_card_service(cards: CardRepo, budgets: BudgetRepo) -> CardService:
    return CardService(cards, budgets)


BudgetSvc = Annotated[BudgetService, Depends(get_budget_service)]
CardSvc = Annotated[CardService, Depends(get_card_service)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], users: UserRepo) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
    user = users.get(user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
