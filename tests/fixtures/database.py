from __future__ import annotations

import os
import tempfile
from typing import Any, Callable, Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.entities.orm import Base


@pytest.fixture
def temp_engine() -> Generator[Engine, None, None]:
    """Create a file-based SQLite engine with all tables created from ORM models.

    Uses a temporary file instead of in-memory SQLite so that the database
    behaves like production (WAL mode, file-based persistence).
    The temp file is automatically cleaned up after the fixture tears down.
    """
    # Create a temporary file for the SQLite database
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    try:
        engine = create_engine(
            f"sqlite:///{db_path}",
            poolclass=None,  # Use default pool for file-based SQLite
            connect_args={"check_same_thread": False},
        )

        # Enable WAL mode and foreign keys on each new connection
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn: Any, connection_record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)
        yield engine
    finally:
        # Clean up the temporary file
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def session_factory(temp_engine: Engine) -> Callable[[], Session]:
    """Create a session factory that produces fresh sessions from the temp engine."""

    def factory() -> Session:
        return Session(temp_engine)

    return factory
