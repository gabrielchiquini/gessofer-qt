from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from frontend.views.order_edit.order_edit_list import OrderEditListView


# ── TC-10: Initial Load ───────────────────────────────────────────


class TestOrderEditListInitialLoad:
    """TC-10: Widget initializes with current month filter and 6-column model."""

    def test_initial_load(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Show the widget and verify initial state after showEvent auto-loads current month."""
        widget = order_list_widget

        # Month filter should be set to current month in MM/yyyy format
        current_text = widget.filter_month.text()
        assert len(current_text) == 7  # "MM/yyyy"
        assert "/" in current_text

        # Input mask and placeholder
        assert widget.filter_month.inputMask() == "99/9999"
        assert widget.filter_month.placeholderText() == "MM/AAAA"

        # Scroll and table should be visible
        assert widget.scroll.isVisible() is True
        assert widget.table_view.isVisible() is True

        # Model should have 6 columns
        assert widget._model.columnCount() == 6


# ── TC-11: Month Navigation ───────────────────────────────────────


class TestOrderEditListMonthNavigation:
    """TC-11: Changing the month filter and clicking Consultar updates the table."""

    def test_month_navigation_changes_orders(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Navigate to July 2024 (3 orders) then August 2024 (2 orders)."""
        widget = order_list_widget

        # Navigate to July 2024
        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        july_count = widget._model.rowCount()
        assert july_count == 3  # 3 orders seeded for July 2024

        # Navigate to August 2024
        widget.filter_month.setText("08/2024")
        widget.btn_search.click()

        aug_count = widget._model.rowCount()
        assert aug_count == 2  # 2 orders seeded for August 2024
        assert aug_count != july_count


# ── TC-12: Order Display ──────────────────────────────────────────


class TestOrderEditListDisplay:
    """TC-12: Table shows correct order data in date ascending order."""

    def test_july_2024_display(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Verify cell-by-cell data for July 2024 orders (ordered by date ASC)."""
        widget = order_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        model = widget._model
        assert model.rowCount() == 3

        # Row 0: 10/07/2024 | Cimento Portland | 2 | 255,00 | 315,00
        assert model.item(0, 0).text() == "10/07/2024"
        assert model.item(0, 1).text() == "Cimento Portland"
        assert model.item(0, 2).text() == "2"
        assert model.item(0, 3).text() == "255,00"
        assert model.item(0, 4).text() == "315,00"

        # Row 1: 15/07/2024 | Areia Premium LTDA | 1 | 300,00 | 335,00
        assert model.item(1, 0).text() == "15/07/2024"
        assert model.item(1, 1).text() == "Areia Premium LTDA"

        # Row 2: 25/07/2024 | Cimento Portland | 1 | 160,00 | 185,00
        assert model.item(2, 0).text() == "25/07/2024"
        assert model.item(2, 1).text() == "Cimento Portland"
        assert model.item(2, 2).text() == "1"
        assert model.item(2, 3).text() == "160,00"
        assert model.item(2, 4).text() == "185,00"

    def test_august_2024_display(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Verify cell-by-cell data for August 2024 orders (ordered by date ASC)."""
        widget = order_list_widget

        widget.filter_month.setText("08/2024")
        widget.btn_search.click()

        model = widget._model
        assert model.rowCount() == 2

        # Row 0: 05/08/2024 | Cimento Portland | 1 | 220,00 | 268,00
        assert model.item(0, 0).text() == "05/08/2024"
        assert model.item(0, 1).text() == "Cimento Portland"
        assert model.item(0, 3).text() == "220,00"
        assert model.item(0, 4).text() == "268,00"

        # Row 1: 20/08/2024 | Tijolo & Cia | 1 | 240,00 | 312,00
        assert model.item(1, 0).text() == "20/08/2024"
        assert model.item(1, 1).text() == "Tijolo & Cia"
        assert model.item(1, 3).text() == "240,00"
        assert model.item(1, 4).text() == "312,00"


# ── TC-13: Empty State ────────────────────────────────────────────


class TestOrderEditListEmptyState:
    """TC-13: Empty state when no orders match the selected month."""

    def test_empty_state_no_orders(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Navigate to a month with no seeded orders and verify empty state."""
        widget = order_list_widget

        widget.filter_month.setText("01/2024")
        widget.btn_search.click()

        assert widget._model.rowCount() == 0
        assert widget.scroll.isVisible() is True
        assert widget.table_view.isVisible() is True


# ── TC-14: Edit Button ────────────────────────────────────────────


class TestOrderEditListEditButton:
    """TC-14: Edit buttons are placed in the Ação column for each row."""

    def test_edit_buttons_present(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Verify Edit buttons are placed in column 5 for each row."""
        widget = order_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        assert widget._model.rowCount() == 3

        for row in range(3):
            index = widget._model.index(row, 5)
            button = widget.table_view.indexWidget(index)
            assert button is not None
            assert isinstance(button, QPushButton)
            assert button.text() == "Editar"


# ── TC-15: Return Key Triggers Search ─────────────────────────────


class TestOrderEditListEnterKeySearch:
    """TC-15: Pressing Enter in the month filter field triggers fetch."""

    def test_return_key_triggers_fetch(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Type a month and emit returnPressed to trigger fetch."""
        widget = order_list_widget

        widget.filter_month.setText("08/2024")
        widget.filter_month.returnPressed.emit()

        assert widget._model.rowCount() == 2
        assert widget._model.item(0, 1).text() == "Cimento Portland"
        assert widget._model.item(1, 1).text() == "Tijolo & Cia"
