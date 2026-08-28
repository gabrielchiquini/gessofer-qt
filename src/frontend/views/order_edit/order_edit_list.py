from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QPushButton, QTableView, QScrollArea,
    QSizePolicy, QMessageBox, QLineEdit, QLabel,
)

from backend.services.order_service import OrderService
from backend.services.xml_import_service import XmlImportService
from backend.utils.currency import cents_to_input, cents_to_view
from backend.utils.date import iso_to_br_date, current_month_orders
from frontend.components.card import Card
from frontend.components.month_filter import MonthFilter
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
_UPLOAD_ICON_PATH: str = str(ASSETS_DIR / "upload.svg")
_PLUS_ICON_PATH: str = str(ASSETS_DIR / "plus.svg")
_SEARCH_ICON_PATH: str = str(ASSETS_DIR / "search.svg")


class OrderEditListView(QWidget):
    """Month-selection bar + order table for order editing."""

    def __init__(
            self,
            parent: QWidget,
            order_service: OrderService,
            xml_import_service: XmlImportService,
            order_edit_dialog_factory: OrderEditDialogFactory,
            nfe_search_dialog_factory: NfeSearchDialogFactory,
    ) -> None:
        super().__init__(parent)
        self._order_service: OrderService = order_service
        self._xml_import_service: XmlImportService = xml_import_service
        self._order_edit_dialog_factory: OrderEditDialogFactory = order_edit_dialog_factory
        self._nfe_search_dialog_factory: NfeSearchDialogFactory = nfe_search_dialog_factory
        self._model: QStandardItemModel = QStandardItemModel(0, 6)
        self._current_month: str = ""
        self.total_label: QLabel = QLabel("Total: 0,00", self)
        self.total_label.setStyleSheet("font-weight: bold;")
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
            self.month_filter.set_month(self._current_month)
            self.fetch_orders()

    def _setup_ui(self) -> None:
        """Build the widget tree."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Filter bar
        filter_frame = self._setup_filter_bar()
        layout.addWidget(filter_frame)

        # Table with scroll area inside Card with footer
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { border: 0px; border-radius: 0px; }")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.table_view = QTableView(self)
        self.table_view.setFrameShape(QFrame.Shape.NoFrame)
        self.table_view.setStyleSheet("QTableView { background-color: white; }")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table_view.verticalHeader().setVisible(False)
        self._model.setHorizontalHeaderLabels([
            "Data", "Fornecedor", "Produtos", "Total Produtos", "Total", "Ação"
        ])
        self._setup_table_size()

        self.table_view.setModel(self._model)
        self.scroll.setWidget(self.table_view)

        # Card container with footer
        self.card = Card(self)
        self.card.set_content(self.scroll)

        footer_layout: QHBoxLayout = QHBoxLayout()
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.addStretch()
        footer_layout.addWidget(self.total_label)
        self.card.set_footer(footer_layout)

        layout.addWidget(self.card, 1)

    def _setup_filter_bar(self) -> QFrame:
        """Create the month filter bar with Consultar and Add buttons."""
        filter_frame = QFrame(self)
        filter_frame.setFrameShape(QFrame.Shape.StyledPanel)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(8)

        self.month_filter = MonthFilter(self)
        self.btn_add = QPushButton("Adicionar Nota", self)
        self.btn_add.setIcon(QIcon(_PLUS_ICON_PATH))
        self.btn_add.setIconSize(QSize(_TABLE_ICON_SIZE, _TABLE_ICON_SIZE))
        self.btn_import_xml = QPushButton("Importar XML", self)
        self.btn_import_xml.setIcon(QIcon(_UPLOAD_ICON_PATH))
        self.btn_import_xml.setIconSize(QSize(_TABLE_ICON_SIZE, _TABLE_ICON_SIZE))
        self.btn_search_xml = QPushButton("Consultar XML", self)
        self.btn_search_xml.setIcon(QIcon(_SEARCH_ICON_PATH))
        self.btn_search_xml.setIconSize(QSize(_TABLE_ICON_SIZE, _TABLE_ICON_SIZE))

        filter_layout.addWidget(self.month_filter)
        filter_layout.addStretch()
        filter_layout.addWidget(self.btn_search_xml)
        filter_layout.addWidget(self.btn_import_xml)
        filter_layout.addWidget(self.btn_add)

        return filter_frame

    def _setup_table(self) -> QTableView:
        """Return the configured table view (created in _setup_ui)."""
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
        self.month_filter.month_selected.connect(self._on_month_selected)
        self.btn_add.clicked.connect(self._on_add_clicked)
        self.btn_import_xml.clicked.connect(self._on_import_xml_clicked)
        self.btn_search_xml.clicked.connect(self._on_consultar_xml_clicked)

    @property
    def filter_month(self) -> QLineEdit:
        """Backward compat: expose MonthFilter's input as filter_month."""
        return self.month_filter.month_input

    @property
    def btn_search(self) -> QPushButton:
        """Backward compat: expose MonthFilter's search button as btn_search."""
        return self.month_filter.search_button

    def fetch_orders(self) -> None:
        """Read current month from input, fetch and display orders."""
        month = self.month_filter.month_input.text().strip()
        if not month:
            return

        self._current_month = month
        try:
            summaries: list[OrderSummary] = self._order_service.fetch_order_summaries(month)
            self._process_orders(summaries)
            self.card.setVisible(True)
        except Exception as exc:
            logger.exception("Error fetching orders: %s", exc)
            self._model.setRowCount(0)
            self.card.setVisible(False)

    def _process_orders(self, summaries: list[OrderSummary]) -> None:
        """Process order summaries and populate the table."""
        self._model.setRowCount(0)

        for summary in summaries:
            date_br: str = iso_to_br_date(summary.date)
            products_total_display: str = cents_to_view(summary.products_total)
            order_total_display: str = cents_to_view(summary.order_total)

            row: list[QStandardItem] = [
                QStandardItem(date_br),
                QStandardItem(summary.supplier),
                QStandardItem(str(summary.product_count)),
                QStandardItem(products_total_display),
                QStandardItem(order_total_display),
                QStandardItem(""),
            ]
            self._model.appendRow(row)

        total: int = sum(s.order_total for s in summaries)
        self.total_label.setText(f"Total: {cents_to_view(total)}")

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

    def _on_month_selected(self, _month: str) -> None:
        """Adapter: MonthFilter emitted month_selected, fetch orders using current input."""
        self.fetch_orders()

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
            success = self._order_service.delete_order(order_id)
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
