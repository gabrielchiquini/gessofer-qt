from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QTableView,
    QScrollArea, QSizePolicy,
)

from bridge.models.order import OrderSummaryDict
from bridge.order_summary import fetch_order_summaries
from backend.utils.currency import cents_to_display
from backend.utils.date import iso_to_br_date, current_month_orders

logger = logging.getLogger(__name__)


class OrderEditListView(QWidget):
    """Month-selection bar + order table with pagination for order editing."""

    order_edited: Signal = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page: int = 1
        self._page_count: int = 1
        self._total: int = 0
        self._model: QStandardItemModel = QStandardItemModel(0, 6)
        self._current_month: str = ""
        self._setup_ui()
        self._connect_signals()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._setup_table_size()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._setup_table_size()
        if not self._current_month:
            self._current_month = current_month_orders()
            self.filter_month.setText(self._current_month)
            self.fetch_orders()

    def _setup_ui(self) -> None:
        """Build the widget tree."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Filter bar
        filter_frame = self._setup_filter_bar()
        layout.addWidget(filter_frame)

        # Table with scroll area
        scroll = self._setup_table()
        layout.addWidget(scroll, 1)

        # Pagination
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)

        self.btn_prev = QPushButton("◀", self)
        self.page_label = QLabel("Página 1 de 1", self)
        self.btn_next = QPushButton("▶", self)

        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.btn_next)

        layout.addLayout(pagination_layout)

    def _setup_filter_bar(self) -> QFrame:
        """Create the month filter bar with Consultar and Add buttons."""
        filter_frame = QFrame(self)
        filter_frame.setFrameShape(QFrame.Shape.StyledPanel)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(8)

        self.filter_month = QLineEdit(self)
        self.filter_month.setInputMask("99/9999")
        self.filter_month.setPlaceholderText("MM/AAAA")
        self.filter_month.returnPressed.connect(self.fetch_orders)

        self.btn_search = QPushButton("Consultar", self)
        self.btn_add = QPushButton("＋ Adicionar Nota", self)

        filter_layout.addWidget(QLabel("Mês", self))
        filter_layout.addWidget(self.filter_month)
        filter_layout.addStretch()
        filter_layout.addWidget(self.btn_search)
        filter_layout.addWidget(self.btn_add)

        return filter_frame

    def _setup_table(self) -> QScrollArea:
        """Create the scrollable table view."""
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.table_view = QTableView(self)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table_view.verticalHeader().setVisible(False)

        self._model.setHorizontalHeaderLabels([
            "Data", "Fornecedor", "Prod.", "Total Prod.", "Total", "Ação"
        ])

        self._setup_table_size()

        scroll.setWidget(self.table_view)
        self.table_view.setModel(self._model)
        return scroll

    def _setup_table_size(self) -> None:
        """Set column widths dynamically based on viewport."""
        total_width = self.table_view.viewport().width()
        self.table_view.setColumnWidth(0, 100)   # Data
        self.table_view.setColumnWidth(2, 60)    # Prod.
        self.table_view.setColumnWidth(3, 140)   # Total Prod.
        self.table_view.setColumnWidth(4, 140)   # Total
        self.table_view.setColumnWidth(5, 100)   # Ação
        remaining = total_width - 100 - 60 - 140 - 140 - 100
        if remaining > 0:
            self.table_view.setColumnWidth(1, remaining)  # Fornecedor

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.btn_search.clicked.connect(self.fetch_orders)
        self.btn_prev.clicked.connect(self.go_previous)
        self.btn_next.clicked.connect(self.go_next)

    def fetch_orders(self) -> None:
        """Read current month from input, fetch and display orders."""
        month = self.filter_month.text().strip()
        if not month:
            return

        self._current_month = month
        try:
            summaries: list[OrderSummaryDict] = fetch_order_summaries(month)
            self._process_orders(summaries)
        except Exception as exc:
            logger.exception("Error fetching orders: %s", exc)
            self._model.setRowCount(0)
            self._total = 0
            self._page_count = 0
            self.update_pagination()

    def _process_orders(self, summaries: list[OrderSummaryDict]) -> None:
        """Process order summaries and populate the table."""
        self._total = len(summaries)
        self._page_count = max(1, self._total)
        self._current_page = 1
        self._model.setRowCount(0)

        for summary in summaries:
            date_br: str = iso_to_br_date(summary["date"])
            products_total_display: str = cents_to_display(summary["products_total"])
            order_total_display: str = cents_to_display(summary["order_total"])

            row: list[QStandardItem] = [
                QStandardItem(date_br),
                QStandardItem(summary["supplier"]),
                QStandardItem(str(summary["product_count"])),
                QStandardItem(products_total_display),
                QStandardItem(order_total_display),
                QStandardItem(""),
            ]
            self._model.appendRow(row)

        # Place "Editar" buttons in the last column
        for row_index, summary in enumerate(summaries):
            edit_btn = QPushButton("[Editar]", self)
            order_id: str = summary["id"]
            edit_btn.clicked.connect(
                lambda checked=False, oid=order_id: self._on_edit_clicked(oid)
            )
            self.table_view.setIndexWidget(
                self._model.index(row_index, 5), edit_btn
            )

        self.update_pagination()

    def _on_edit_clicked(self, order_id: str) -> None:
        """Handle Edit button click — emit order_edited signal."""
        self.order_edited.emit(order_id)

    def go_previous(self) -> None:
        """Go to the previous page."""
        if self._current_page > 1:
            self._current_page -= 1
            self._refresh_page()

    def go_next(self) -> None:
        """Go to the next page."""
        if self._current_page < self._page_count:
            self._current_page += 1
            self._refresh_page()

    def update_pagination(self) -> None:
        """Update the pagination label and button states."""
        self.page_label.setText(
            f"Página {self._current_page} de {self._page_count}"
        )
        self.btn_prev.setEnabled(self._current_page > 1)
        self.btn_next.setEnabled(self._current_page < self._page_count)

    def _refresh_page(self) -> None:
        """Fetch and display the current page."""
        summaries: list[OrderSummaryDict] = fetch_order_summaries(
            self._current_month
        )
        self._process_orders(summaries)
