from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from entities.base_entity import BaseEntity


class User(BaseEntity):
    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
