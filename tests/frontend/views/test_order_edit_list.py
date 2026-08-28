from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QMessageBox, QWidget
from pytestqt.qtbot import QtBot

from backend.utils.currency import cents_to_input
from backend.utils.date import datetime_to_br_date
from frontend.views.order_edit.order_edit_list import OrderEditListView
from tests.fixtures.seed_data import ORDERS_DATA


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

        # Row 0: Order A (ORDERS_DATA[0])
        assert model.item(0, 0).text() == datetime_to_br_date(ORDERS_DATA[0].date)
        assert model.item(0, 1).text() == ORDERS_DATA[0].supplier
        assert model.item(0, 2).text() == str(len(ORDERS_DATA[0].products))
        assert model.item(0, 3).text() == cents_to_input(sum(p.total for p in ORDERS_DATA[0].products))
        assert model.item(0, 4).text() == cents_to_input(
            sum(p.total for p in ORDERS_DATA[0].products) + ORDERS_DATA[0].freight + ORDERS_DATA[0].unloading
        )

        # Row 1: Order B (ORDERS_DATA[1])
        assert model.item(1, 0).text() == datetime_to_br_date(ORDERS_DATA[1].date)
        assert model.item(1, 1).text() == ORDERS_DATA[1].supplier

        # Row 2: Order E (ORDERS_DATA[4])
        assert model.item(2, 0).text() == datetime_to_br_date(ORDERS_DATA[4].date)
        assert model.item(2, 1).text() == ORDERS_DATA[4].supplier
        assert model.item(2, 2).text() == str(len(ORDERS_DATA[4].products))
        assert model.item(2, 3).text() == cents_to_input(sum(p.total for p in ORDERS_DATA[4].products))
        assert model.item(2, 4).text() == cents_to_input(
            sum(p.total for p in ORDERS_DATA[4].products) + ORDERS_DATA[4].freight + ORDERS_DATA[4].unloading
        )

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

        # Row 0: Order C (ORDERS_DATA[2])
        assert model.item(0, 0).text() == datetime_to_br_date(ORDERS_DATA[2].date)
        assert model.item(0, 1).text() == ORDERS_DATA[2].supplier
        assert model.item(0, 3).text() == cents_to_input(sum(p.total for p in ORDERS_DATA[2].products))
        assert model.item(0, 4).text() == cents_to_input(
            sum(p.total for p in ORDERS_DATA[2].products) + ORDERS_DATA[2].freight + ORDERS_DATA[2].unloading
        )

        # Row 1: Order D (ORDERS_DATA[3])
        assert model.item(1, 0).text() == datetime_to_br_date(ORDERS_DATA[3].date)
        assert model.item(1, 1).text() == ORDERS_DATA[3].supplier
        assert model.item(1, 3).text() == cents_to_input(sum(p.total for p in ORDERS_DATA[3].products))
        assert model.item(1, 4).text() == cents_to_input(
            sum(p.total for p in ORDERS_DATA[3].products) + ORDERS_DATA[3].freight + ORDERS_DATA[3].unloading
        )


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
        assert widget.table_view.isVisible() is True


# ── TC-14: Edit Button ────────────────────────────────────────────


class TestOrderEditListEditButton:
    """TC-14: Each row in the Ação column has a container widget with edit and delete icon-only buttons."""

    def test_edit_delete_buttons_in_container(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Verify column 5 contains a QWidget container with 2 icon-only QPushButton children."""
        widget = order_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        assert widget._model.rowCount() == 3

        for row in range(3):
            index = widget._model.index(row, 5)
            container = widget.table_view.indexWidget(index)

            # Column 5 should hold a QWidget container, not a direct button
            assert container is not None
            assert isinstance(container, QWidget)

            # The container should have exactly 2 child widgets (edit + delete)
            children = container.findChildren(QPushButton)
            assert len(children) == 2

            # First button: edit icon
            edit_btn = children[0]
            assert not edit_btn.icon().isNull(), "Edit button should have an icon"

            # Second button: delete icon
            delete_btn = children[1]
            assert not delete_btn.icon().isNull(), "Delete button should have an icon"

            # Both buttons should be icon-only (no text)
            assert edit_btn.text() == ""
            assert delete_btn.text() == ""


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
        assert widget._model.item(0, 1).text() == ORDERS_DATA[2].supplier
        assert widget._model.item(1, 1).text() == ORDERS_DATA[3].supplier


# ── TC-16: Delete Button Present ──────────────────────────────────


class TestOrderEditListDeleteButtonPresent:
    """TC-16: Each row in the Ação column has a delete button alongside the edit button."""

    def test_delete_button_exists_in_each_row(
            self,
            order_list_widget: OrderEditListView,
    ) -> None:
        """Verify every row has a delete button (index 1) with icon and tooltip."""
        widget = order_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        assert widget._model.rowCount() == 3

        for row in range(3):
            index = widget._model.index(row, 5)
            container = widget.table_view.indexWidget(index)

            assert container is not None
            assert isinstance(container, QWidget)

            buttons = container.findChildren(QPushButton)
            assert len(buttons) >= 2

            delete_btn = buttons[1]
            assert isinstance(delete_btn, QPushButton)
            assert delete_btn.icon() is not None
            assert delete_btn.text() == ""
            assert delete_btn.toolTip() == "Excluir pedido"


# ── TC-17: Delete Confirmation Dialog ─────────────────────────────


class TestOrderEditListDeleteConfirmation:
    """TC-17: Clicking delete shows a confirmation dialog with Yes/No buttons."""

    def test_delete_shows_confirmation_dialog(
            self,
            order_list_widget: OrderEditListView,
            qtbot: QtBot,
    ) -> None:
        """Clicking delete opens QMessageBox.warning with Yes/No buttons."""
        widget = order_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        # Get the delete button from row 0
        index = widget._model.index(0, 5)
        container = widget.table_view.indexWidget(index)
        buttons = container.findChildren(QPushButton)
        delete_btn = buttons[1]

        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            mock_warning.return_value = QMessageBox.StandardButton.Yes
            qtbot.addWidget(delete_btn)
            qtbot.mouseClick(delete_btn, Qt.MouseButton.LeftButton)

        mock_warning.assert_called_once()
        call_args = mock_warning.call_args

        # First positional arg after self is the parent (widget)
        # Second positional arg is the title
        # Third positional arg is the message
        # Fourth positional arg is the buttons
        title = call_args[0][1]
        message = call_args[0][2]
        buttons_arg = call_args[0][3]

        assert "Confirmar" in title
        assert "excluir" in message.lower()
        assert QMessageBox.StandardButton.Yes in buttons_arg
        assert QMessageBox.StandardButton.No in buttons_arg


# ── TC-18: Delete Cancel Path ─────────────────────────────────────


class TestOrderEditListDeleteCancel:
    """TC-18: Cancelling the delete dialog does not call delete_order or refresh."""

    def test_delete_cancel_does_not_call_bridge(
            self,
            order_list_widget: OrderEditListView,
            qtbot: QtBot,
    ) -> None:
        """Clicking No in the confirmation dialog skips delete and refresh."""
        widget = order_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        initial_row_count = widget._model.rowCount()
        assert initial_row_count == 3

        # Get the delete button from row 0
        index = widget._model.index(0, 5)
        container = widget.table_view.indexWidget(index)
        buttons = container.findChildren(QPushButton)
        delete_btn = buttons[1]

        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            mock_warning.return_value = QMessageBox.StandardButton.No
            with patch.object(widget._order_service, "delete_order") as mock_delete:
                qtbot.addWidget(delete_btn)
                qtbot.mouseClick(delete_btn, Qt.MouseButton.LeftButton)

                mock_delete.assert_not_called()

        # Table should NOT have been refreshed
        assert widget._model.rowCount() == initial_row_count


# ── TC-19: Delete Success Path ────────────────────────────────────


class TestOrderEditListDeleteSuccess:
    """TC-19: Confirming delete calls bridge.delete_order and refreshes the table."""

    def test_delete_confirmed_calls_bridge_and_refreshes(
            self,
            order_list_widget: OrderEditListView,
            qtbot: QtBot,
    ) -> None:
        """Clicking Yes calls delete_order then refreshes the table."""
        widget = order_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        # Get the delete button from row 0
        index = widget._model.index(0, 5)
        container = widget.table_view.indexWidget(index)
        buttons = container.findChildren(QPushButton)
        delete_btn = buttons[1]

        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            mock_warning.return_value = QMessageBox.StandardButton.Yes
            with patch.object(widget._order_service, "delete_order", return_value=True) as mock_delete:
                with patch.object(widget, "fetch_orders") as mock_fetch:
                    qtbot.addWidget(delete_btn)
                    qtbot.mouseClick(delete_btn, Qt.MouseButton.LeftButton)

                    mock_delete.assert_called_once()
                    # Verify delete_order was called with a string order ID
                    call_args = mock_delete.call_args
                    assert len(call_args[0]) == 1
                    assert isinstance(call_args[0][0], str)

                    mock_fetch.assert_called_once()


# ── TC-20: Delete Error Path ──────────────────────────────────────


class TestOrderEditListDeleteError:
    """TC-20: When delete_order returns False, a critical error dialog is shown."""

    def test_delete_failure_shows_error_dialog(
            self,
            order_list_widget: OrderEditListView,
            qtbot: QtBot,
    ) -> None:
        """Delete failure shows QMessageBox.critical and does not refresh the table."""
        widget = order_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        # Get the delete button from row 0
        index = widget._model.index(0, 5)
        container = widget.table_view.indexWidget(index)
        buttons = container.findChildren(QPushButton)
        delete_btn = buttons[1]

        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            mock_warning.return_value = QMessageBox.StandardButton.Yes
            with patch.object(widget._order_service, "delete_order", return_value=False) as mock_delete:
                with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_critical:
                    with patch.object(widget, "fetch_orders") as mock_fetch:
                        qtbot.addWidget(delete_btn)
                        qtbot.mouseClick(delete_btn, Qt.MouseButton.LeftButton)

                        mock_delete.assert_called_once()
                        mock_critical.assert_called_once()

                        # Verify critical dialog title and message
                        critical_args = mock_critical.call_args
                        title = critical_args[0][1]
                        message = critical_args[0][2]
                        assert title == "Erro"
                        assert "Erro ao excluir" in message

                        # Table should NOT have been refreshed on error
                        mock_fetch.assert_not_called()
