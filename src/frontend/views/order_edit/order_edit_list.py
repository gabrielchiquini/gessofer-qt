from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QTableView,
    QSizePolicy, QMessageBox,
)

from backend.services.xml_import_service import XmlImportService
from backend.utils.currency import cents_to_display
from backend.utils.date import iso_to_br_date, current_month_orders
from bridge.order import OrderBridge
from bridge.order_summary import OrderSummaryBridge
from models.order import OrderSummary
from util.paths import ASSETS_DIR

_TABLE_BUTTON_SIZE = 28
_TABLE_ICON_SIZE = 14

if TYPE_CHECKING:
    from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory
    from frontend.factories.nfe_search_dialog_factory import NfeSearchDialogFactory

logger = logging.getLogger(__name__)

_EDIT_ICON_PATH: str = str(ASSETS_DIR / "edit.svg")
_DELETE_ICON_PATH: str = str(ASSETS_DIR / "trash.svg")


class OrderEditListView(QWidget):
    """Month-selection bar + order table for order editing."""

    def __init__(
            self,
            parent: QWidget,
            order_bridge: OrderBridge,
            order_summary_bridge: OrderSummaryBridge,
            xml_import_service: XmlImportService,
            order_edit_dialog_factory: OrderEditDialogFactory,
            nfe_search_dialog_factory: NfeSearchDialogFactory,
    ) -> None:
        super().__init__(parent)
        self._order_bridge: OrderBridge = order_bridge
        self._order_summary_bridge: OrderSummaryBridge = order_summary_bridge
        self._xml_import_service: XmlImportService = xml_import_service
        self._order_edit_dialog_factory: OrderEditDialogFactory = order_edit_dialog_factory
        self._nfe_search_dialog_factory: NfeSearchDialogFactory = nfe_search_dialog_factory
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
        table = self._setup_table()
        layout.addWidget(table, 1)

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

    def _setup_table(self) -> QTableView:
        """Create the scrollable table view."""

        self.table_view = QTableView(self)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalScrollBar().setVisible(False)

        self._model.setHorizontalHeaderLabels([
            "Data", "Fornecedor", "Produtos", "Total Produtos", "Total", "Ação"
        ])

        self._setup_table_size()

        self.table_view.setModel(self._model)
        return self.table_view

    def _setup_table_size(self) -> None:
        """Set column widths dynamically based on viewport."""
        total_width = self.table_view.viewport().width()
        self.table_view.setColumnWidth(0, 100)  # Data
        self.table_view.setColumnWidth(2, 60)  # Prod.
        self.table_view.setColumnWidth(3, 140)  # Total Prod.
        self.table_view.setColumnWidth(4, 140)  # Total
        self.table_view.setColumnWidth(5, 100)  # Ação
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
            summaries: list[OrderSummary] = self._order_summary_bridge.fetch_order_summaries(month)
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

        # Place edit + delete buttons in the last column
        for row_index, summary in enumerate(summaries):
            edit_btn = QPushButton("", self)
            edit_btn.setIcon(QIcon(_EDIT_ICON_PATH))
            edit_btn.setIconSize(QSize(_TABLE_ICON_SIZE, _TABLE_ICON_SIZE))
            edit_btn.setFixedSize(_TABLE_BUTTON_SIZE, _TABLE_BUTTON_SIZE)
            edit_btn.setToolTip("Editar pedido")
            order_id: str = summary.id
            edit_btn.clicked.connect(
                lambda checked=False, oid=order_id: self._on_edit_clicked(oid)
            )
            delete_btn = QPushButton("", self)
            delete_btn.setIcon(QIcon(_DELETE_ICON_PATH))
            delete_btn.setIconSize(QSize(_TABLE_ICON_SIZE, _TABLE_ICON_SIZE))
            delete_btn.setFixedSize(_TABLE_BUTTON_SIZE, _TABLE_BUTTON_SIZE)
            delete_btn.setToolTip("Excluir pedido")
            delete_btn.clicked.connect(
                lambda checked=False, oid=order_id: self._on_delete_clicked(oid)
            )
            container_widget = QWidget()
            container_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            container_layout = QHBoxLayout(container_widget)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(2)
            container_layout.addWidget(edit_btn)
            container_layout.addWidget(delete_btn)
            self.table_view.setIndexWidget(
                self._model.index(row_index, 5), container_widget
            )

    def _on_edit_clicked(self, order_id: str) -> None:
        """Handle Edit button click — open the order edit dialog."""
        dialog = self._order_edit_dialog_factory(self, order_id, None)
        dialog.order_saved.connect(self._on_order_saved)
        dialog.show()

    def _on_delete_clicked(self, order_id: str) -> None:
        """Handle Delete button click — confirm and remove the order."""
        reply = QMessageBox.warning(
            self,
            "Confirmar Exclusão",
            "Tem certeza que deseja excluir este pedido? Esta ação não pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self._order_bridge.delete_order(order_id)
            if success:
                self.fetch_orders()
            else:
                QMessageBox.critical(
                    self,
                    "Erro",
                    "Erro ao excluir o pedido. Tente novamente.",
                )

    def _on_add_clicked(self) -> None:
        """Handle Add button click — open a blank order edit dialog."""
        dialog = self._order_edit_dialog_factory(self, None, None)
        dialog.order_saved.connect(self._on_order_saved)
        dialog.show()

    def _on_import_xml_clicked(self) -> None:
        """Handle Importar XML button click — open file dialog, parse XML, show dialog."""
        from pathlib import Path as PathLib
        from PySide6.QtWidgets import QFileDialog

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
        result = self._xml_import_service.parse_file(str(PathLib(file_path).resolve()))

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
        dialog = self._order_edit_dialog_factory(self, None, order)
        dialog.order_saved.connect(self._on_order_saved)
        dialog.show()

    def _on_consultar_xml_clicked(self) -> None:
        """Handle Consultar XML button click — open NFe search dialog."""
        dialog = self._nfe_search_dialog_factory(self)
        dialog.nfe_result.connect(self._on_nfe_result)
        dialog.show()

    def _on_nfe_result(self, xml_path: str) -> None:
        """Handle successful NFe search — import XML and open edit dialog."""

        result = self._xml_import_service.parse_file(xml_path)

        if not result.orders:
            QMessageBox.critical(
                self,
                "Erro ao importar XML",
                "Nenhum pedido encontrado no XML baixado da SEFAZ.",
            )
            return

        order = result.orders[0]
        edit_dialog = self._order_edit_dialog_factory(self, None, order)
        edit_dialog.order_saved.connect(self._on_order_saved)
        edit_dialog.show()

    def _on_order_saved(self, order_data: object) -> None:
        """Handle successful order save — refresh the order table."""
        self.fetch_orders()
