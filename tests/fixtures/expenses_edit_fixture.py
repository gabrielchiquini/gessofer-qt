from __future__ import annotations

from typing import Generator

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from bridge.expense import ExpenseBridge
from di.injector_module import get_injector
from frontend.factories.expense_edit_dialog_factory import ExpenseEditDialogFactory
from frontend.views.expense_edit.expense_edit_dialog import ExpenseEditDialog


@pytest.fixture
def expense_edit_dialog(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[ExpenseEditDialog, None, None]:
    """Create an ExpenseEditDialog for July 2024 wired to the test database."""
    injector = get_injector()
    expense_edit_dialog_factory: ExpenseEditDialogFactory = injector.get(ExpenseEditDialogFactory)

    dialog = expense_edit_dialog_factory(parent=None, month="07/2024")
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def expense_edit_dialog_august(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[ExpenseEditDialog, None, None]:
    """Create an ExpenseEditDialog for August 2024 wired to the test database."""
    injector = get_injector()
    expense_edit_dialog_factory: ExpenseEditDialogFactory = injector.get(ExpenseEditDialogFactory)

    dialog = expense_edit_dialog_factory(parent=None, month="08/2024")
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def expense_edit_dialog_january(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[ExpenseEditDialog, None, None]:
    """Create an ExpenseEditDialog for January 2024 (no seeded expenses) wired to the test database."""
    injector = get_injector()
    expense_edit_dialog_factory: ExpenseEditDialogFactory = injector.get(ExpenseEditDialogFactory)

    dialog = expense_edit_dialog_factory(parent=None, month="01/2024")
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()
