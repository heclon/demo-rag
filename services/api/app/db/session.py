"""SQLAlchemy engine/session wiring plus a thin raw-SQL execution helper.

The SQL-RAG path needs to execute LLM-generated, read-only SQL directly
(see app/rag/sql_rag.py::execute_safe_sql), so we expose both the ORM
session (for typed CRUD) and a raw connection helper (for that path).
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context-manager form for use outside request handlers (scripts, tests)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
