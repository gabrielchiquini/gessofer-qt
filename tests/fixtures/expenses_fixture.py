from __future__ import annotations

from typing import Generator

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from frontend.views.expense_list import ExpenseListView

from PySide6.QtWidgets import QWidget
from backend.services.expense_service import ExpenseService
from frontend.factories.expense_edit_dialog_factory import ExpenseEditDialogFactory


@pytest.fixture
def expense_list_widget(
        temp_engine: Engine,  # Changed from expense_test_env: None
        qtbot: QtBot,
) -> Generator["ExpenseListView", None, None]:
    """Create an ExpenseListView wired to the test database."""
    from di.injector_module import get_injector

    injector = get_injector()
    expense_service: ExpenseService = injector.get(ExpenseService)
    expense_edit_dialog_factory: ExpenseEditDialogFactory = injector.get(ExpenseEditDialogFactory)

    widget = ExpenseListView(
        parent=None,
        expense_service=expense_service,
        expense_edit_dialog_factory=expense_edit_dialog_factory,
    )
    qtbot.addWidget(widget)
    widget.show()
    yield widget
    widget.deleteLater()
