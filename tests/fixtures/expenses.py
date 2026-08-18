from __future__ import annotations

import os
import tempfile
from datetime import datetime
from typing import Generator, Any

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.entities.orm import Base, Expense
from frontend.views.expense_list import ExpenseListView
from tests.util.bridge_reset import reset_bridge_singletons

from PySide6.QtWidgets import QWidget
from bridge.expense import ExpenseBridge
from frontend.factories import ExpenseEditDialogFactory


# ── Seed data ─────────────────────────────────────────────────────
#
# Seed data (insertion order = ID order = display order):
# - ID 1: 2024-07, "Material de escritório", 15000 cents (R$150,00)
# - ID 2: 2024-07, "Taxa bancária", 7500 cents (R$75,00)
# - ID 3: 2024-07, "Limpeza", 30000 cents (R$300,00)
# - ID 4: 2024-08, "Manutenção elétrica", 45000 cents (R$450,00)
# - ID 5: 2024-08, "Água e esgoto", 12000 cents (R$120,00)


def _seed_expenses(engine: Engine) -> None:
    """Seed the EXPENSE table with known test data.

    Args:
        engine: The SQLAlchemy engine to use for seeding.
    """
    now = datetime.now()

    expenses_data = [
        ("2024-07", "Material de escritório", 15000),
        ("2024-07", "Taxa bancária", 7500),
        ("2024-07", "Limpeza", 30000),
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


@pytest.fixture
def expense_test_env(
        monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Set up the full test environment: temp-file DB + injector + patched get_engine.

    This fixture creates a file-based temporary database, seeds expense data,
    patches get_engine() so that both the fetch handler and the save handler
    use the SAME database.

    The temporary file is automatically cleaned up after the fixture tears down.
    """
    # Step 1: Create a temporary file for the SQLite database
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    try:
        # Create engine with WAL mode and foreign keys
        engine = create_engine(
            f"sqlite:///{db_path}",
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
        _seed_expenses(engine)

        # Step 2: Patch get_engine to return our seeded engine
        import backend.database.connection
        original_get_engine = backend.database.connection.get_engine
        backend.database.connection.get_engine = lambda: engine  # type: ignore[assignment]

        # Step 3: Reset bridge singletons
        reset_bridge_singletons()

        # Step 4: Reset the app injector so get_injector() creates a fresh one
        # with the patched get_engine()
        import injector_module
        injector_module._app_injector = None

        # Step 5: Call get_injector() which creates a fresh Injector using the patched get_engine()
        from injector_module import get_injector
        injector = get_injector()

        yield
    finally:
        # Teardown
        import backend.database.connection
        backend.database.connection.get_engine = original_get_engine  # type: ignore[assignment]
        import injector_module
        injector_module._app_injector = None
        reset_bridge_singletons()
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def expense_list_widget(
        expense_test_env: None,
        qtbot: QtBot,
) -> Generator["ExpenseListView", None, None]:
    """Create an ExpenseListView wired to the test database."""
    from injector_module import get_injector

    injector = get_injector()
    expense_bridge: ExpenseBridge = injector.get(ExpenseBridge)
    expense_edit_dialog_factory: ExpenseEditDialogFactory = injector.get(ExpenseEditDialogFactory)

    _parent = QWidget()
    widget = ExpenseListView(
        parent=_parent,
        expense_bridge=expense_bridge,
        expense_edit_dialog_factory=expense_edit_dialog_factory,
    )
    qtbot.addWidget(widget)
    widget.show()
    yield widget
    widget.deleteLater()
    _parent.deleteLater()
