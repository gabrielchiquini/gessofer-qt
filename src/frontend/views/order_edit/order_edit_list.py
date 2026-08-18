from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QTableView,
    QScrollArea, QSizePolicy,
)

from models.order import OrderSummary
from bridge.order_summary import fetch_order_summaries, OrderSummaryBridge
from bridge.nfe import NfeBridge
from backend.utils.currency import cents_to_display
from backend.utils.date import iso_to_br_date, current_month_orders
from frontend.business import import_xml, BusinessService
from bridge.order import OrderBridge

logger = logging.getLogger(__name__)

_EDIT_ICON: QIcon = QIcon(str(Path(__file__).parent.parent.parent / "assets" / "edit.svg"))


class OrderEditListView(QWidget):
    """Month-selection bar + order table for order editing."""

    def __init__(
        self,
        parent: QWidget | None = None,
        order_bridge: OrderBridge | None = None,
        order_summary_bridge: OrderSummaryBridge | None = None,
        business_service: BusinessService | None = None,
        nfe_bridge: NfeBridge | None = None,
    ) -> None:
        super().__init__(parent)
        self._order_bridge: OrderBridge | None = order_bridge
        self._order_summary_bridge: OrderSummaryBridge | None = order_summary_bridge
        self._business_service: BusinessService | None = business_service
        self._nfe_bridge: NfeBridge | None = nfe_bridge
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
        self.btn_import_xml = QPushButton("Importar XML", self)
        self.btn_search_xml = QPushButton("Consultar XML", self)

        filter_layout.addWidget(QLabel("Mês", self))
        filter_layout.addWidget(self.filter_month)
        filter_layout.addWidget(self.btn_search)
        filter_layout.addStretch()
        filter_layout.addWidget(self.btn_search_xml)
        filter_layout.addWidget(self.btn_import_xml)
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
            "Data", "Fornecedor", "Produtos", "Total Produtos", "Total", "Ação"
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
        self.btn_add.clicked.connect(self._on_add_clicked)
        self.btn_import_xml.clicked.connect(self._on_import_xml_clicked)
        self.btn_search_xml.clicked.connect(self._on_consultar_xml_clicked)

    def fetch_orders(self) -> None:
        """Read current month from input, fetch and display orders."""
        month = self.filter_month.text().strip()
        if not month:
            return

        self._current_month = month
        try:
            if self._order_summary_bridge is not None:
                summaries: list[OrderSummary] = self._order_summary_bridge.fetch_order_summaries(month)
            else:
                summaries: list[OrderSummary] = fetch_order_summaries(month)
            self._process_orders(summaries)
        except Exception as exc:
            logger.exception("Error fetching orders: %s", exc)
            self._model.setRowCount(0)

    def _process_orders(self, summaries: list[OrderSummary]) -> None:
        """Process order summaries and populate the table."""
        self._model.setRowCount(0)

        for summary in summaries:
            date_br: str = iso_to_br_date(summary.date)
            products_total_display: str = cents_to_display(summary.products_total)
            order_total_display: str = cents_to_display(summary.order_total)

            row: list[QStandardItem] = [
                QStandardItem(date_br),
                QStandardItem(summary.supplier),
                QStandardItem(str(summary.product_count)),
                QStandardItem(products_total_display),
                QStandardItem(order_total_display),
                QStandardItem(""),
            ]
            self._model.appendRow(row)

        # Place "Editar" buttons in the last column
        for row_index, summary in enumerate(summaries):
            edit_btn = QPushButton(_EDIT_ICON, "Editar", self)
            order_id: str = summary.id
            edit_btn.clicked.connect(
                lambda checked=False, oid=order_id: self._on_edit_clicked(oid)
            )
            self.table_view.setIndexWidget(
                self._model.index(row_index, 5), edit_btn
            )

    def _on_edit_clicked(self, order_id: str) -> None:
        """Handle Edit button click — open the order edit dialog."""
        from frontend.views.order_edit.order_edit_dialog import OrderEditDialog

        dialog = OrderEditDialog(
            self,
            order_id=order_id,
        )
        dialog.order_saved.connect(self._on_order_saved)
        dialog.exec()

    def _on_add_clicked(self) -> None:
        """Handle Add button click — open a blank order edit dialog."""
        from frontend.views.order_edit.order_edit_dialog import OrderEditDialog

        month: str = self.filter_month.text().strip()
        dialog = OrderEditDialog(
            self,
            order_id=None,
        )
        dialog.order_saved.connect(self._on_order_saved)
        dialog.exec()

    def _on_import_xml_clicked(self) -> None:
        """Handle Importar XML button click — open file dialog, parse XML, show dialog."""
        from pathlib import Path as PathLib
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from frontend.views.order_edit.order_edit_dialog import OrderEditDialog

        # 1. Open file dialog
        file_path: str = ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo XML",
            "",
            "Arquivos XML (*.xml)",
        )
        if not file_path:
            return  # User cancelled

        # 2. Parse XML
        if self._business_service is not None:
            result = self._business_service.import_xml(str(PathLib(file_path).resolve()))
        else:
            result = import_xml(str(PathLib(file_path).resolve()))

        # 3. Handle result
        if not result.orders:
            QMessageBox.critical(
                self,
                "Erro ao importar XML",
                "Nenhum pedido encontrado no arquivo XML selecionado.",
            )
            return

        # 4. Open OrderEditDialog pre-populated with the parsed order
        order = result.orders[0]  # Single NFe → single order
        dialog = OrderEditDialog(self, order=order)
        dialog.order_saved.connect(self._on_order_saved)
        dialog.exec()

    def _on_consultar_xml_clicked(self) -> None:
        """Handle Consultar XML button click — open NFe search dialog."""
        from frontend.nfe_search_dialog import NfeSearchDialog

        dialog = NfeSearchDialog(self)
        dialog.nfe_result.connect(self._on_nfe_result)
        dialog.exec()

    def _on_nfe_result(self, xml_path: str) -> None:
        """Handle successful NFe search — import XML and open edit dialog."""
        from PySide6.QtWidgets import QMessageBox

        from frontend.business import import_xml
        from frontend.views.order_edit.order_edit_dialog import OrderEditDialog

        if self._nfe_bridge is not None:
            result_path: str = self._nfe_bridge.search_nfe_key(xml_path)
        else:
            from bridge.nfe import search_nfe_key
            result_path = search_nfe_key(xml_path)

        if self._business_service is not None:
            result = self._business_service.import_xml(result_path)
        else:
            result = import_xml(result_path)

        if not result.orders:
            QMessageBox.critical(
                self,
                "Erro ao importar XML",
                "Nenhum pedido encontrado no XML baixado da SEFAZ.",
            )
            return

        order = result.orders[0]
        edit_dialog = OrderEditDialog(self, order=order)
        edit_dialog.order_saved.connect(self._on_order_saved)
        edit_dialog.exec()

    def _on_order_saved(self, order_data: object) -> None:
        """Handle successful order save — refresh the order table."""
        self.fetch_orders()


