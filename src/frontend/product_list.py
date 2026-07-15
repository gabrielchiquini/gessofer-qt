from __future__ import annotations

import logging
import traceback
from typing import Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QTableView,
    QScrollArea, QHeaderView,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

from backend.utils.currency import cents_to_display
from backend.utils.date import iso_to_br_date
from bridge import ProductPageResponseDict
from frontend.constants import PRODUCT_PAGE_SIZE
from widgets.product import fetch_products


logger = logging.getLogger(__name__)


class ProductListView(QWidget):
    """Filter form + QTableView with pagination for product data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page: int = 1
        self._page_count: int = 1
        self._total: int = 0
        self._model: QStandardItemModel = QStandardItemModel(0, 6)
        self._setup_ui()
        self._connect_signals()
        self.clear_filters()

    def _setup_ui(self) -> None:
        """Build the widget tree."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Filter form
        filter_frame = QFrame(self)
        filter_frame.setFrameShape(QFrame.Shape.StyledPanel)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(8)

        self.filter_supplier = QLineEdit(self)
        self.filter_supplier.setPlaceholderText("Fornecedor")

        self.filter_product = QLineEdit(self)
        self.filter_product.setPlaceholderText("Produto")

        self.filter_month = QLineEdit(self)
        self.filter_month.setInputMask("99/9999")
        self.filter_month.setFixedWidth(100)
        self.filter_month.setPlaceholderText("MM/AAAA")

        self.btn_search = QPushButton("Consultar", self)
        self.btn_clear = QPushButton("Limpar", self)

        filter_layout.addWidget(QLabel("Fornecedor", self))
        filter_layout.addWidget(self.filter_supplier)
        filter_layout.addWidget(QLabel("Produto", self))
        filter_layout.addWidget(self.filter_product)
        filter_layout.addWidget(QLabel("Mês", self))
        filter_layout.addWidget(self.filter_month)
        filter_layout.addWidget(self.btn_search)
        filter_layout.addWidget(self.btn_clear)

        layout.addWidget(filter_frame)

        # Table with scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.table_view = QTableView(self)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self._setup_model()

        scroll.setWidget(self.table_view)
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

    def _setup_model(self) -> None:
        """Configure the QStandardItemModel."""
        self._model.setHorizontalHeaderLabels([
            "Data", "Fornecedor", "Produto", "Preço", "Total", "Pedido"
        ])
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.setModel(self._model)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.btn_search.clicked.connect(self.search)
        self.btn_clear.clicked.connect(self.clear_filters)
        self.btn_prev.clicked.connect(self.go_previous)
        self.btn_next.clicked.connect(self.go_next)

    def search(self) -> None:
        """Apply filters and reload page 1."""
        self._current_page = 1
        self._refresh_page()

    def clear_filters(self) -> None:
        """Clear all filters and reload page 1."""
        self.filter_supplier.clear()
        self.filter_product.clear()
        self.filter_month.clear()
        self._current_page = 1
        self._refresh_page()

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
        self.page_label.setText(f"Página {self._current_page} de {self._page_count}")
        self.btn_prev.setEnabled(self._current_page > 1)
        self.btn_next.setEnabled(self._current_page < self._page_count)

    def _refresh_page(self) -> None:
        """Fetch and display the current page."""

        supplier = self.filter_supplier.text().strip()
        product = self.filter_product.text().strip()
        month = self.filter_month.text().strip()

        try:
            result = fetch_products(
                self._current_page,
                supplier if supplier else "",
                product if product else "",
                month if month else "",
            )
            self._process_result(result)
        except Exception as exc:
            logger.error(traceback.format_exc())
            self._model.setRowCount(0)
            self._total = 0
            self._page_count = 0
            self.update_pagination()

    def _process_result(self, result: ProductPageResponseDict) -> None:
        """Process a fetch result and populate the table."""
        self._total = result["total"]
        self._page_count = result["page_count"]
        self._model.setRowCount(0)

        for item in result.get("items", []):
            row: list[QStandardItem] = [
                QStandardItem(iso_to_br_date(item.get("date", ""))),
                QStandardItem(item.get("supplier", "")),
                QStandardItem(item.get("name", "")),
                QStandardItem(item.get("price", 0)),
                QStandardItem(item.get("totalPrice", 0)),
                QStandardItem(item.get("orderId", "")),
            ]
            self._model.appendRow(row)

        self.update_pagination()
