import os
from pathlib import Path
from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import Engine


DEFAULT_DB_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "gessofer-tauri")
DEFAULT_DB_FILE = "main.db"
TEST_DB_PREFIX = "tmp-gessofer-tauri"


def discover_database_path() -> str:
    """
    Discover the database file path using the priority order:
    1. DATABASE_URL environment variable (development/tests)
    2. %LOCALAPPDATA%\\gessofer-tauri\\main.db (production)
    3. %TEMP%\\tmp-gessofer-tauri.db (tests fallback)

    Returns the absolute path as a string.
    Raises FileNotFoundError if no database is found and no env var is set.
    """
    # Step 1: Check DATABASE_URL
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Strip "sqlite://" prefix if present
        path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        return os.path.abspath(path)

    # Step 2: Check production path
    prod_path = os.path.join(DEFAULT_DB_DIR, DEFAULT_DB_FILE)
    if os.path.isfile(prod_path):
        return os.path.abspath(prod_path)

    # Step 3: Check test path
    temp_dir = os.environ.get("TEMP", os.environ.get("TMP", ""))
    if temp_dir:
        test_path = os.path.join(temp_dir, f"{TEST_DB_PREFIX}.db")
        if os.path.isfile(test_path):
            return os.path.abspath(test_path)

    raise FileNotFoundError(
        "Nenhum arquivo de banco encontrado. "
        "Defina DATABASE_URL ou coloque main.db em %LOCALAPPDATA%\\gessofer-tauri\\"
    )


def get_engine(db_path: str | None = None) -> Engine:
    """
    Return a SQLAlchemy Engine configured for SQLite.

    Uses StaticPool with check_same_thread=False for desktop-app thread safety.
    WAL mode and foreign keys are enabled via connect_args PRAGMA settings.

    If db_path is None, calls discover_database_path().

    The database schema (tables) is assumed to already exist externally.
    This function does NOT create or initialize the schema.
    """
    if db_path is None:
        db_path = discover_database_path()

    engine = create_engine(
        f"sqlite:///{db_path}",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Enable WAL mode and foreign keys on each new connection
    from sqlalchemy.event import register

    @register(engine, "connect")
    def set_sqlite_pragma(dbapi_conn: Any, connection_record: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
