from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame,
    QTableView, QScrollArea, QHBoxLayout, QSizePolicy, QLabel,
)

from bridge.expense import fetch_expenses_for_month
from bridge.models.expense import ExpenseOutput as BridgeExpense, ExpensesForMonthOutput
from backend.utils.currency import cents_to_display
from backend.utils.date import current_month_orders
from frontend.components import Card
from frontend.components.month_filter import MonthFilter

logger = logging.getLogger(__name__)


class ExpenseListView(QWidget):
    """Month filter + expenses table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_month: str = ""
        self._model: QStandardItemModel = QStandardItemModel(0, 2)
        self.total_label: QLabel = QLabel("Total: R$ 0,00", self)
        self._setup_ui()
        self._connect_signals()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._setup_table_size()

    def showEvent(self, event: object) -> None:
        super().showEvent(event)
        self._setup_table_size()
        if not self._current_month:
            self.month_filter.set_month(current_month_orders())
            self.fetch_expenses(self.month_filter.get_month())

    def _setup_ui(self) -> None:
        """Build the widget tree."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Filter bar
        filter_frame = QFrame(self)
        filter_frame.setFrameShape(QFrame.Shape.StyledPanel)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(8)

        self.month_filter = MonthFilter(self)
        filter_layout.addWidget(self.month_filter)
        filter_layout.addStretch()

        # Table with scroll area
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { border: 0px; border-radius: 0px; }")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.table_view = QTableView(self)
        self.table_view.setFrameShape(QFrame.Shape.NoFrame)
        self.table_view.setFrameShadow(QFrame.Shadow.Plain)
        self.table_view.setStyleSheet("QTableView {     background-color: white; }")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setModel(self._model)

        self.table_view.verticalHeader().setVisible(False)

        self._model.setHorizontalHeaderLabels(["Despesa", "Valor"])

        self._setup_table_size()

        self.scroll.setWidget(self.table_view)

        # Card container with footer
        self.card = Card(self)
        self.card.set_content(self.scroll)

        footer_layout: QHBoxLayout = QHBoxLayout()
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_label: QLabel = QLabel("Total:", self)
        footer_label.setStyleSheet("font-weight: bold;")
        footer_layout.addWidget(footer_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.total_label)
        self.card.set_footer(footer_layout)

        layout.addWidget(filter_frame)
        layout.addWidget(self.card, 1)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.month_filter.month_selected.connect(self.fetch_expenses)

    def fetch_expenses(self, month: str) -> None:
        """Fetch and display expenses for the given month."""
        if not month or not month.strip():
            return

        self._current_month = month
        try:
            result: ExpensesForMonthOutput = fetch_expenses_for_month(month)
            self._process_expenses(result.expenses)
            self.total_label.setText(f"Total: {cents_to_display(result.total)}")
            self.scroll.setVisible(True)
            self.card.setVisible(True)
        except Exception as exc:
            logger.exception("Error fetching expenses: %s", exc)
            self._model.setRowCount(0)
            self.scroll.setVisible(False)
            self.card.setVisible(False)

    def _process_expenses(self, expenses: list[BridgeExpense]) -> None:
        """Process expense items and populate the table."""
        self._model.setRowCount(0)

        for expense in expenses:
            desc_item = QStandardItem(expense.description)
            value_item = QStandardItem(cents_to_display(expense.value))
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row: list[QStandardItem] = [desc_item, value_item]
            self._model.appendRow(row)

        self.table_view.verticalScrollBar().setValue(0)

    def clear_filters(self) -> None:
        """Clear all filters and hide the table."""
        self.month_filter.clear()
        self._current_month = ""
        self.scroll.setVisible(False)
        self.card.setVisible(False)

    def _setup_table_size(self) -> None:
        """Set column widths dynamically based on viewport."""
        total_width = self.table_view.viewport().width()

        col_0_width = int(total_width * 0.6)
        col_1_width = total_width - col_0_width

        self.table_view.setColumnWidth(0, col_0_width)
        self.table_view.setColumnWidth(1, col_1_width)
