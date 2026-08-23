from __future__ import annotations

from typing import Generator

import pytest
from PySide6.QtWidgets import QApplication, QDialog
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from frontend.app import MainWindow
from frontend.views.expense_edit.expense_edit_dialog import ExpenseEditDialog
from frontend.views.expense_list import ExpenseListView
from frontend.factories.product_list_view_factory import ProductListViewFactory
from frontend.factories.order_edit_list_view_factory import OrderEditListViewFactory
from frontend.factories.expense_list_view_factory import ExpenseListViewFactory
from frontend.factories.certificate_status_view_factory import CertificateStatusViewFactory
from di.injector_module import get_injector


# ── Shared Fixture ──────────────────────────────────────────────────


@pytest.fixture
def main_window_with_factories(
    temp_engine: Engine, qtbot: QtBot,
) -> Generator[MainWindow, None, None]:
    """Create a MainWindow with all factories wired to the test database."""
    injector = get_injector()
    plvf: ProductListViewFactory = injector.get(ProductListViewFactory)
    oelf: OrderEditListViewFactory = injector.get(OrderEditListViewFactory)
    elvf: ExpenseListViewFactory = injector.get(ExpenseListViewFactory)
    csvf: CertificateStatusViewFactory = injector.get(CertificateStatusViewFactory)

    mw = MainWindow(
        product_list_view_factory=plvf,
        order_edit_list_view_factory=oelf,
        expense_list_view_factory=elvf,
        certificate_status_view_factory=csvf,
    )
    qtbot.addWidget(mw)
    mw.show()
    yield mw
    mw.close()
    mw.deleteLater()


# ── Helper ──────────────────────────────────────────────────────────


def _get_dialog_by_type[T](class_type: type[T]) -> T:
    """Find a visible QDialog whose window title starts with the given prefix."""
    dialogs = [
        w for w in QApplication.topLevelWidgets()
        if isinstance(w, class_type)
    ]
    assert dialogs, f"No dialog found with title starting with: {class_type!r}"
    return dialogs[-1]


# ── TC-01: Edit Expenses and Verify List Updates ────────────────────

class TestExpenseListEdit:
    """TC-01: Edit an existing expense and add a new one, verify list updates."""

    def test_edit_and_add_expenses(
        self,
        main_window_with_factories: MainWindow,
        qtbot: QtBot,
    ) -> None:
        """Navigate to expense list, verify 3 expenses in July 2024,
        edit first expense and add a new one, verify 4 expenses with updated data."""
        mw = main_window_with_factories

        # Step 1: Navigate to expense list
        mw._on_item_clicked("Lista", "Despesas")
        expense_view: ExpenseListView = mw.centralWidget() # type: ignore[union-attr]
        assert isinstance(expense_view, ExpenseListView)

        # Step 2: Verify initial state — 3 expenses in July 2024
        expense_view.month_filter.set_month("07/2024")
        expense_view.month_filter.search_button.click()
        qtbot.wait(200)
        assert expense_view._model.rowCount() == 3

        # Step 3: Open expense edit dialog
        expense_view.btn_edit.click()
        qtbot.wait(100)

        dialog = _get_dialog_by_type(ExpenseEditDialog)
        qtbot.addWidget(dialog)
        qtbot.waitExposed(dialog)

        # Step 4: Edit the first expense (row 0)
        rows = dialog.items_card.get_expense_rows()
        rows[0].name_input.setText("Material de escritório EDITADO")
        rows[0].value_input.setText("200,00")

        # Step 5: Add a new expense
        dialog.items_card.add_row()
        rows = dialog.items_card.get_expense_rows()
        # After add_row, the new row is at index -2 (before the trailing empty row)
        rows[-2].name_input.setText("Nova despesa")
        rows[-2].value_input.setText("50,00")

        dialog.btn_save.click()
        qtbot.wait(200)

        # Step 6: Verify expense list updated to 4 expenses
        assert expense_view._model.rowCount() == 4

        # Step 7: Verify the edited expense appears with correct data
        assert expense_view._model.item(0, 0).text() == "Material de escritório EDITADO"
        assert expense_view._model.item(0, 1).text() == "200,00"


# ── TC-02: Delete Expense and Verify List Updates ───────────────────

class TestExpenseListDelete:
    """TC-02: Delete an expense row and verify the list updates."""

    def test_delete_expense(
        self,
        main_window_with_factories: MainWindow,
        qtbot: QtBot,
    ) -> None:
        """Navigate to expense list, verify 3 expenses in July 2024,
        delete the middle expense, verify 2 expenses remain with correct data."""
        mw = main_window_with_factories

        # Step 1: Navigate to expense list
        mw._on_item_clicked("Lista", "Despesas")
        expense_view: ExpenseListView = mw.centralWidget() # type: ignore[union-attr]
        assert isinstance(expense_view, ExpenseListView)

        # Step 2: Verify initial state — 3 expenses in July 2024
        expense_view.month_filter.set_month("07/2024")
        expense_view.month_filter.search_button.click()
        qtbot.wait(200)
        assert expense_view._model.rowCount() == 3

        # Step 3: Open expense edit dialog
        expense_view.btn_edit.click()
        qtbot.wait(100)

        dialog = _get_dialog_by_type(ExpenseEditDialog)
        qtbot.addWidget(dialog)
        qtbot.waitExposed(dialog)

        # Step 4: Delete the middle expense (row 1 — "Taxa bancária")
        # There are 4 rows: 3 data rows + 1 trailing empty
        rows = dialog.items_card.get_expense_rows()
        rows[1].delete_button.click()
        qtbot.wait(100)

        # Step 5: Save — remaining rows (excluding trailing empty) are saved
        dialog.btn_save.click()
        qtbot.wait(200)


        # Step 6: Verify expense list updated to 2 expenses
        assert expense_view._model.rowCount() == 2

        # Step 7: Verify remaining expenses are correct
        assert expense_view._model.item(0, 0).text() == "Material de escritório"
        assert expense_view._model.item(1, 0).text() == "Limpeza"
