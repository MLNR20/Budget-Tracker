from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from entities.base_entity import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class BaseRepository(Generic[T]):
    """Generic CRUD repository. Subclass and set `model`, then add entity-specific queries."""

    model: type[T]

    def __init__(self, session: Session):
        self.session = session

    def get(self, entity_id: int) -> T | None:
        return self.session.get(self.model, entity_id)

    def list(
        self, skip: int = 0, limit: int = 100, order_by: Sequence[Any] = (), **filters: Any
    ) -> Sequence[T]:
        stmt = select(self.model).filter_by(**filters)
        if order_by:
            stmt = stmt.order_by(*order_by)
        return self.session.scalars(stmt.offset(skip).limit(limit)).all()

    def first(self, **filters: Any) -> T | None:
        return self.session.scalars(select(self.model).filter_by(**filters).limit(1)).first()

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def update(self, entity: T, values: dict[str, Any]) -> T:
        for field, value in values.items():
            setattr(entity, field, value)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, entity: T) -> None:
        """Hard delete. For soft delete, update `is_active` to False instead."""
        self.session.delete(entity)
        self.session.commit()
