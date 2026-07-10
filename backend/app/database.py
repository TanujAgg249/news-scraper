"""
SQLAlchemy database engine, session factory, and FastAPI dependency.
Uses synchronous SQLite for the prototype.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.config import settings

# ---------------------------------------------------------------------------
# Engine — use check_same_thread=False for SQLite so multiple threads work
# ---------------------------------------------------------------------------
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables that don't yet exist."""
    from app import models  # noqa: F401 — import so models are registered
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created / verified.")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
