from fastapi import APIRouter, HTTPException, status

from dependencies import CurrentUser, UserRepo
from entities.user import User
from schemas import UserCreate, UserResponse, UserUpdate
from security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, users: UserRepo):
    email = data.email.lower()
    if users.get_by_email(email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        email=email,
        hashed_password=hash_password(data.password),
    )
    return users.add(user)


@router.get("/me", response_model=UserResponse)
def read_me(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(data: UserUpdate, current_user: CurrentUser, users: UserRepo):
    values = data.model_dump(exclude_unset=True, exclude_none=True)

    if "email" in values:
        values["email"] = values["email"].lower()
        existing = users.get_by_email(values["email"])
        if existing and existing.id != current_user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    if "password" in values:
        values["hashed_password"] = hash_password(values.pop("password"))

    return users.update(current_user, values)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_me(current_user: CurrentUser, users: UserRepo):
    """Soft delete: the account is kept but can no longer log in or authenticate."""
    users.update(current_user, {"is_active": False})
