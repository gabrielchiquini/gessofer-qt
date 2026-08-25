from __future__ import annotations

import os
import tempfile
from datetime import datetime
from typing import Any, Callable, Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import di.injector_module
from backend.entities.orm import Base, Expense, Order, Product
from backend.utils.text import normalize_text
from tests.fixtures.seed_data import EXPENSES_DATA, ORDERS_DATA
from tests.util.bridge_reset import reset_bridge_singletons


# ── Seed helpers ──────────────────────────────────────────────────


def _seed_expenses(engine: Engine) -> None:
    """Seed the EXPENSE table with known test data.

    Args:
        engine: The SQLAlchemy engine to use for seeding.
    """
    now = datetime.now()
    with Session(engine) as session:
        for expense in EXPENSES_DATA:
            expense_obj = Expense(
                MONTH=expense.month,
                DESCRIPTION=expense.description,
                VALUE=expense.value,
                CREATED_AT=now,
                UPDATED_AT=now,
            )
            session.add(expense_obj)
        session.commit()


def _seed_orders(engine: Engine) -> None:
    """Seed the ORDER and PRODUCT tables with known test data.

    Args:
        engine: The SQLAlchemy engine to use for seeding.
    """
    now = datetime.now()
    with Session(engine) as session:
        for order in ORDERS_DATA:
            order_obj = Order(
                ID=order.id,
                DATE=order.date,
                SUPPLIER=order.supplier,
                SUPPLIER_NORMALIZED=normalize_text(order.supplier),
                NFE_KEY=order.nfe_key,
                FREIGHT=order.freight,
                UNLOADING=order.unloading,
                CREATED_AT=now,
                UPDATED_AT=now,
            )
            session.add(order_obj)
            for prod in order.products:
                product_obj = Product(
                    ID=prod.id,
                    NAME=prod.name,
                    NAME_NORMALIZED=normalize_text(prod.name),
                    QUANTITY=prod.quantity,
                    PRICE=prod.price,
                    PRICE_WITH_FREIGHT=prod.price_with_freight,
                    TOTAL_PRICE=prod.total,
                    ORDER_ID=order.id,
                    ITEM_ORDINAL=prod.ordinal,
                    CREATED_AT=now,
                    UPDATED_AT=now,
                )
                session.add(product_obj)
        session.commit()


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def temp_engine() -> Generator[Engine, None, None]:
    """Create a file-based SQLite engine with all tables created from ORM models.

    Uses a temporary file instead of in-memory SQLite so that the database
    behaves like production (WAL mode, file-based persistence).
    The temp file is automatically cleaned up after the fixture tears down.

    Side effects (shared by ALL tests that depend on this fixture or any
    fixture depending on it):
      - Seeds both expense and order/product data into the same DB.
      - Patches ``di.injector_module.get_engine`` so the DI container
        resolves the test engine instead of the real ``main.db``.
      - Resets bridge singletons so no stale handlers survive across tests.
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

        # Seed both expenses and orders into the same DB
        _seed_expenses(engine)
        _seed_orders(engine)

        # Patch DI so get_injector() uses this engine.
        # injector_module.py imports get_engine via
        #   "from backend.database.connection import get_engine"
        # so the name "get_engine" lives in di.injector_module's namespace.
        original_get_engine: Callable[[], Engine] = di.injector_module.get_engine  # type: ignore[assignment]
        di.injector_module.get_engine = lambda: engine  # type: ignore[assignment]

        # Reset bridge singletons so DI resolves fresh with the patched engine
        reset_bridge_singletons()

        yield engine
    finally:
        # Restore original get_engine and reset DI
        di.injector_module.get_engine = original_get_engine  # type: ignore[assignment]
        reset_bridge_singletons()
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


@pytest.fixture
def fetch_handler(session_factory: Callable[[], Session]) -> "FetchHandler":
    """FetchHandler backed by the test database (already seeded by temp_engine)."""
    from bridge.product import FetchHandler
    return FetchHandler(session_factory)
