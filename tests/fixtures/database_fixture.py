from __future__ import annotations

import os
import tempfile
from datetime import date as date_type, datetime
from typing import Any, Callable, Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.entities.orm import Base, Expense, Order, Product
from backend.utils.text import normalize_text
import di.injector_module
from di.injector_module import get_engine
from tests.util.bridge_reset import reset_bridge_singletons


# ── Seed helpers ──────────────────────────────────────────────────


def _seed_expenses(engine: Engine) -> None:
    """Seed the EXPENSE table with known test data.

    Args:
        engine: The SQLAlchemy engine to use for seeding.
    """
    now = datetime.now()

    expenses_data = [
        ("2024-07", "Material de escritório", 15000),
        ("2024-07", "Taxa bancária", 7500),
        ("2024-07", "Limpeza", 150000),
        ("2024-08", "Manutenção elétrica", 45000),
        ("2024-08", "Água e esgoto", 12000),
    ]

    with Session(engine) as session:
        for month, description, value in expenses_data:
            expense = Expense(
                MONTH=month,
                DESCRIPTION=description,
                VALUE=value,
                CREATED_AT=now,
                UPDATED_AT=now,
            )
            session.add(expense)
        session.commit()


def _seed_orders(engine: Engine) -> None:
    """Seed the ORDER and PRODUCT tables with known test data.

    Args:
        engine: The SQLAlchemy engine to use for seeding.
    """
    now = datetime.now()

    orders_data = [
        # Order A: July 2024, Cimento Portland
        (
            "order-a",
            date_type(2024, 7, 10),
            "Cimento Portland",
            "45678901234567",
            5000,
            1000,
            [
                ("prod-a1", "Cimento CP-II 50kg", 1, 25000, 25000, 1),
                ("prod-a2", "Cimento CP-II 1kg", 1, 500, 500, 2),
            ],
        ),
        # Order B: July 2024, Areia Premium LTDA
        (
            "order-b",
            date_type(2024, 7, 15),
            "Areia Premium LTDA",
            "12345678901234",
            3000,
            500,
            [
                ("prod-b1", "Areia média", 2, 120000, 240000, 1),
            ],
        ),
        # Order C: August 2024, Cimento Portland
        (
            "order-c",
            date_type(2024, 8, 5),
            "Cimento Portland",
            "98765432109876",
            4000,
            800,
            [
                ("prod-c1", "Cimento CP-I 50kg", 1, 22000, 22000, 1),
            ],
        ),
        # Order D: August 2024, Tijolo & Cia
        (
            "order-d",
            date_type(2024, 8, 20),
            "Tijolo & Cia",
            "11223344556677",
            6000,
            1200,
            [
                ("prod-d1", "Tijolo cerâmico 8 furos", 20, 1200, 24000, 1),
            ],
        ),
        # Order E: July 2024, Cimento Portland
        (
            "order-e",
            date_type(2024, 7, 25),
            "Cimento Portland",
            "55667788990011",
            2000,
            500,
            [
                ("prod-e1", "Cal hidratada 20kg", 2, 8000, 16000, 1),
            ],
        ),
    ]

    with Session(engine) as session:
        for order_id, order_date, supplier, nfe_key, freight, unloading, products in orders_data:
            order = Order(
                ID=order_id,
                DATE=order_date,
                SUPPLIER=supplier,
                SUPPLIER_NORMALIZED=normalize_text(supplier),
                NFE_KEY=nfe_key,
                FREIGHT=freight,
                UNLOADING=unloading,
                CREATED_AT=now,
                UPDATED_AT=now,
            )
            session.add(order)
            for prod_id, prod_name, qty, price, total, ordinal in products:
                product = Product(
                    ID=prod_id,
                    NAME=prod_name,
                    NAME_NORMALIZED=normalize_text(prod_name),
                    QUANTITY=qty,
                    PRICE=price,
                    TOTAL_PRICE=total,
                    ORDER_ID=order_id,
                    ITEM_ORDINAL=ordinal,
                    CREATED_AT=now,
                    UPDATED_AT=now,
                )
                session.add(product)
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
