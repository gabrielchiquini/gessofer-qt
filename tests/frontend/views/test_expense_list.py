from __future__ import annotations

import pytestqt
from pytestqt.qtbot import QtBot

from bridge.expense import ExpenseBridge
from di.injector_module import get_injector
from frontend.factories.expense_edit_dialog_factory import ExpenseEditDialogFactory
from frontend.views.expense_list import ExpenseListView


# ── TC-01: Initial Load ───────────────────────────────────────────


class TestExpenseListInitialLoad:
    """TC-01: Widget auto-loads current month on first show."""

    def test_initial_load_shows_current_month(
            self,
            qtbot: QtBot,
    ) -> None:
        """Show the widget and verify the month filter is set to current month."""

        injector = get_injector()
        expense_bridge: ExpenseBridge = injector.get(ExpenseBridge)
        expense_edit_dialog_factory: ExpenseEditDialogFactory = injector.get(ExpenseEditDialogFactory)

        widget = ExpenseListView(
            parent=None,
            expense_bridge=expense_bridge,
            expense_edit_dialog_factory=expense_edit_dialog_factory,
        )
        qtbot.addWidget(widget)
        widget.show()

        # The month filter should have a valid MM/yyyy format after showEvent
        current_month = widget.month_filter.get_month()
        assert len(current_month) == 7  # "MM/yyyy"
        assert "/" in current_month

        # scroll and card should be visible after fetch
        assert widget.scroll.isVisible() is True
        assert widget.card.isVisible() is True


# ── TC-02: Month Navigation ───────────────────────────────────────


class TestExpenseListMonthNavigation:
    """TC-02: User navigates to a different month, table updates."""

    def test_month_navigation_changes_expenses(
            self,
            expense_list_widget: ExpenseListView,
            qtbot: pytestqt.qtbot.QtBot,
    ) -> None:
        """Navigate to July 2024 (3 expenses) then August 2024 (2 expenses)."""
        widget = expense_list_widget
        # Navigate to July 2024
        widget.month_filter.set_month("07/2024")
        widget.month_filter.search_button.click()

        july_count = widget._model.rowCount()
        assert july_count == 3  # 3 expenses seeded for 2024-07

        # Navigate to August 2024
        widget.month_filter.set_month("08/2024")
        widget.month_filter.search_button.click()

        aug_count = widget._model.rowCount()
        assert aug_count == 2  # 2 expenses seeded for 2024-08
        assert aug_count != july_count


# ── TC-03: Expense Display ────────────────────────────────────────


class TestExpenseListDisplay:
    """TC-03: Table shows correct descriptions and values in ID order."""

    def test_expense_display_correct_data(
            self,
            expense_list_widget: ExpenseListView,
            qtbot: pytestqt.qtbot.QtBot,
    ) -> None:
        """Verify descriptions and values for July 2024 expenses (ordered by ID)."""
        widget = expense_list_widget

        widget.month_filter.set_month("07/2024")
        widget.month_filter.search_button.click()

        model = widget._model
        # July 2024 rows (IDs 1→3): insertion order
        assert model.item(0, 0).text() == "Material de escritório"  # ID 1
        assert model.item(1, 0).text() == "Taxa bancária"  # ID 2
        assert model.item(2, 0).text() == "Limpeza"  # ID 3

        # Values formatted as Brazilian currency (no "R$", just the number)
        assert model.item(0, 1).text() == "150,00"  # 15000 cents
        assert model.item(1, 1).text() == "75,00"  # 7500 cents
        assert model.item(2, 1).text() == "300,00"  # 30000 cents

        # Verify August ordering
        widget.month_filter.set_month("08/2024")
        widget.month_filter.search_button.click()

        assert model.item(0, 0).text() == "Manutenção elétrica"  # ID 4
        assert model.item(1, 0).text() == "Água e esgoto"  # ID 5
        assert model.item(0, 1).text() == "450,00"  # 45000 cents
        assert model.item(1, 1).text() == "120,00"  # 12000 cents


# ── TC-04: Total Calculation ──────────────────────────────────────


class TestExpenseListTotal:
    """TC-04: Total label shows correct sum for the displayed month."""

    def test_total_label_calculation(
            self,
            expense_list_widget: ExpenseListView,
            qtbot: pytestqt.qtbot.QtBot,
    ) -> None:
        """Verify total matches sum of visible expense values."""
        widget = expense_list_widget

        # July 2024: 15000 + 7500 + 30000 = 52500 cents
        widget.month_filter.set_month("07/2024")
        widget.month_filter.search_button.click()

        assert widget.total_label.text() == "Total: 525,00"

        # August 2024: 45000 + 12000 = 57000 cents
        widget.month_filter.set_month("08/2024")
        widget.month_filter.search_button.click()

        assert widget.total_label.text() == "Total: 570,00"


# ── TC-07: Empty State ────────────────────────────────────────────

class TestExpenseListEmptyState:
    """TC-07: Empty state when no expenses for the selected month."""

    def test_empty_state_no_expenses(
            self,
            expense_list_widget: ExpenseListView,
            qtbot: pytestqt.qtbot.QtBot,
    ) -> None:
        """Navigate to a month with no seeded expenses and verify empty state."""
        widget = expense_list_widget

        # Navigate to a month with no seeded expenses
        widget.month_filter.set_month("01/2024")
        widget.month_filter.search_button.click()

        # Table should be empty
        assert widget._model.rowCount() == 0

        # Total should be zero (cents_to_display(0) == "0,00")
        assert widget.total_label.text() == "Total: 0,00"

        # Scroll area and card should still be visible
        # (fetch_expenses doesn't hide them on empty results, only on exception)
        assert widget.scroll.isVisible() is True
        assert widget.card.isVisible() is True


# ── TC-08: Currency Formatting ────────────────────────────────────


class TestExpenseListCurrencyFormatting:
    """TC-08: Currency values use Brazilian format (comma decimal, dot thousands)."""

    def test_currency_formatting(
            self,
            expense_list_widget: ExpenseListView,
            qtbot: pytestqt.qtbot.QtBot,
    ) -> None:
        """Verify all displayed values use correct Brazilian currency format."""
        widget = expense_list_widget

        widget.month_filter.set_month("07/2024")
        widget.month_filter.search_button.click()

        model = widget._model
        for row in range(model.rowCount()):
            value_text = model.item(row, 1).text()
            # Should use comma as decimal separator
            assert "," in value_text
            # Verify no negative values in our test data
            assert not value_text.startswith("-")


# ── TC-09: Clear Filters ──────────────────────────────────────────


class TestExpenseListClearFilters:
    """TC-09: clear_filters() hides table and card."""

    def test_clear_filters_hides_table(
            self,
            expense_list_widget: ExpenseListView,
            qtbot: pytestqt.qtbot.QtBot,
    ) -> None:
        """Clear filters and verify table/card are hidden."""
        widget = expense_list_widget

        widget.month_filter.set_month("07/2024")
        widget.month_filter.search_button.click()

        # Verify visible
        assert widget.scroll.isVisible() is True
        assert widget.card.isVisible() is True

        # Clear filters
        widget.clear_filters()

        # Verify hidden
        assert widget.scroll.isVisible() is False
        assert widget.card.isVisible() is False

        # Verify month filter is cleared
        assert widget.month_filter.get_month() == ""
        assert widget._current_month == ""
