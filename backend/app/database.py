"""
SQLAlchemy database engine, session factory, and FastAPI dependency.
Uses synchronous SQLite for the prototype.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
engine_kwargs = {"echo": False, "pool_pre_ping": True}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # PostgreSQL connection pooling for Supabase
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables that don't yet exist."""
    from app import models  # noqa: F401 — import so models are registered
    from app.logger import logger
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created / verified.")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
