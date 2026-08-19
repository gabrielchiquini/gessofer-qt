from __future__ import annotations

import logging
from operator import floordiv

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

from PySide6.QtWidgets import (
    QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QTableView,
    QScrollArea, )
from frontend.components import Card

from models.output import PageResponse, ProductListItem
from bridge.product import ProductBridge

logger = logging.getLogger(__name__)


class ProductListView(QWidget):
    """Filter form + QTableView with pagination for product data."""
    table_view: QTableView

    def __init__(self, parent: QWidget, product_bridge: ProductBridge) -> None:
        super().__init__(parent)
        self._product_bridge: ProductBridge = product_bridge
        self._current_page: int = 1
        self._page_count: int = 1
        self._total: int = 0
        self._model: QStandardItemModel = QStandardItemModel(0, 5)
        self._setup_ui()
        self._connect_signals()
        self.clear_filters()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._setup_table_size()

    def showEvent(self, event):
        super().showEvent(event)
        self._setup_table_size()

    def _setup_ui(self) -> None:
        """Build the widget tree."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Filter form
        filter_card = Card(self)
        filter_card.set_title("Filtro")
        filter_card.set_content(self._setup_filter())

        layout.addWidget(filter_card)

        # Table with scroll area and pagination footer
        table_card = Card(self)
        self._setup_table()
        table_card.set_content(self.scroll)

        # Pagination
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)

        self.btn_prev = QPushButton("◀", self)
        self.page_label = QLabel("Página 1 de 1", self)
        self.btn_next = QPushButton("▶", self)

        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.btn_next)

        table_card.set_footer(pagination_layout)

        layout.addWidget(table_card, 1)

    def _setup_filter(self) -> QFrame:
        filter_frame = QFrame(self)
        filter_frame.setFrameShape(QFrame.Shape.NoFrame)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(6, 6, 6, 6)
        filter_layout.setSpacing(8)

        self.filter_supplier = QLineEdit(self)
        self.filter_supplier.setPlaceholderText("Fornecedor")
        self.filter_supplier.returnPressed.connect(self.search)

        self.filter_product = QLineEdit(self)
        self.filter_product.setPlaceholderText("Produto")
        self.filter_product.returnPressed.connect(self.search)

        self.filter_month = QLineEdit(self)
        self.filter_month.setInputMask("99/9999")
        self.filter_month.setPlaceholderText("MM/AAAA")
        self.filter_month.returnPressed.connect(self.search)

        self.btn_search = QPushButton("Consultar", self)
        self.btn_clear = QPushButton("Limpar", self)

        # Vertical layout: label + input for supplier
        supplier_layout = QVBoxLayout()
        supplier_layout.setContentsMargins(0, 0, 0, 0)
        supplier_layout.addWidget(QLabel("Fornecedor", self))
        supplier_layout.addWidget(self.filter_supplier)
        filter_layout.addLayout(supplier_layout)

        # Vertical layout: label + input for product
        product_layout = QVBoxLayout()
        product_layout.setContentsMargins(0, 0, 0, 0)
        product_layout.addWidget(QLabel("Produto", self))
        product_layout.addWidget(self.filter_product)
        filter_layout.addLayout(product_layout)

        # Vertical layout: label + input for month
        month_layout = QVBoxLayout()
        month_layout.setContentsMargins(0, 0, 0, 0)
        month_layout.addWidget(QLabel("Mês", self))
        month_layout.addWidget(self.filter_month)
        filter_layout.addLayout(month_layout)

        # Buttons aligned to the bottom of the input rows
        filter_layout.addWidget(self.btn_search, alignment=Qt.AlignmentFlag.AlignBottom)
        filter_layout.addWidget(self.btn_clear, alignment=Qt.AlignmentFlag.AlignBottom)

        return filter_frame

    def _setup_table(self) -> None:
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

        """Configure the QStandardItemModel."""
        self._model.setHorizontalHeaderLabels([
            "Data", "Fornecedor", "Produto", "Preço", "Total"
        ])

        self._setup_table_size()

        self.scroll.setWidget(self.table_view)

        self.table_view.setModel(self._model)

    def _setup_table_size(self):
        total_width = self.table_view.viewport().width()
        self.table_view.setColumnWidth(0, 100)
        self.table_view.setColumnWidth(3, 150)
        self.table_view.setColumnWidth(4, 150)
        total_width -= 100 + 150 + 150
        self.table_view.setColumnWidth(1, floordiv(total_width, 2))
        self.table_view.setColumnWidth(2, floordiv(total_width, 2))

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
            result = self._product_bridge.fetch_products(
                self._current_page,
                supplier if supplier else "",
                product if product else "",
                month if month else "",
            )
            self._process_result(result)
        except Exception as exc:
            logging.exception(exc, exc_info=True)
            self._model.setRowCount(0)
            self._total = 0
            self._page_count = 0
            self.update_pagination()

    def _process_result(self, result: PageResponse[ProductListItem]) -> None:
        """Process a fetch result and populate the table."""
        self._total = result.total
        self._page_count = result.page_count
        self._model.setRowCount(0)

        for item in result.items:
            row: list[QStandardItem] = [
                QStandardItem(item.date),
                QStandardItem(item.supplier),
                QStandardItem(item.name),
                QStandardItem(item.price),
                QStandardItem(item.total_price),
            ]
            self._model.appendRow(row)
        self.table_view.verticalScrollBar().setValue(0)
        self.update_pagination()
