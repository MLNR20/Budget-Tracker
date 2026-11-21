import warnings
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL


def _build_engine():
    url = make_url(DATABASE_URL)

    if url.get_backend_name() == "sqlite":
        # SQLite has no native Decimal type; SQLAlchemy warns about it. Amounts have 2 decimal
        # places and are converted back to Decimal on read, so the warning is noise.
        warnings.filterwarnings("ignore", message=".*does not support Decimal objects natively.*")
        # check_same_thread=False: FastAPI runs sync endpoints in a thread pool.
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _record):
            # SQLite ignores foreign keys (and ON DELETE rules) unless enabled per connection.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    # PostgreSQL: use the psycopg (v3) driver whatever scheme the URL was written with.
    if url.drivername in ("postgresql", "postgres"):
        url = url.set(drivername="postgresql+psycopg")
    return create_engine(
        url,
        pool_pre_ping=True,  # serverless hosts (e.g. Neon) drop idle connections
        pool_recycle=300,
        # Neon's pooled endpoint uses PgBouncer, which doesn't support server-side prepared statements.
        connect_args={"prepare_threshold": None},
    )


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base every ORM entity ultimately inherits from."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    # Import entities so they register on Base.metadata before create_all.
    import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
