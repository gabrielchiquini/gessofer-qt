from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bridge.models.order import OrderDict, OrderInputDict
from bridge.order import fetch_order_by_id, save_orders
from frontend.business import import_xml
from frontend.order_card_widget import OrderCardWidget
from backend.utils.currency import cents_to_display


class OrderEditDialog(QDialog):
    """Modal dialog for editing a single order."""

    order_saved: Signal = Signal(object)
    closed: Signal = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        order_id: str | None = None,
        initial_month: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo Pedido" if order_id is None else "Editar Pedido")
        self.setModal(True)
        self.setMinimumSize(600, 500)

        # ── Header Bar ────────────────────────────────────────────────
        # self.month_filter: QLineEdit = QLineEdit(self)
        # self.month_filter.setInputMask("99/9999")
        # self.month_filter.setPlaceholderText("MM/AAAA")
        # if initial_month:
        #     self.month_filter.setText(initial_month)
        #
        # self.btn_import_xml: QPushButton = QPushButton("Importar XML", self)
        # self.message_label: QLabel = QLabel(self)
        # self.message_label.setWordWrap(True)

        # ── Single Order Card ─────────────────────────────────────────
        if order_id:
            order_data: OrderDict | None = fetch_order_by_id(order_id)
            if order_data is None:
                self.order_card: OrderCardWidget = OrderCardWidget(self)
            else:
                self.order_card = OrderCardWidget(self, order_data=order_data)
        else:
            self.order_card = OrderCardWidget(self)

        # ── Footer Buttons ────────────────────────────────────────────
        self.btn_save: QPushButton = QPushButton("Salvar", self)
        self.btn_close: QPushButton = QPushButton("Fechar", self)

        # ── Main Layout ───────────────────────────────────────────────
        layout: QVBoxLayout = QVBoxLayout(self)
        # layout.setContentsMargins(12, 12, 12, 12)

        # # Header frame
        # header_frame = QHBoxLayout()
        # header_frame.addWidget(QLabel("Mês", self))
        # header_frame.addWidget(self.month_filter)
        # header_frame.addStretch()
        # header_frame.addWidget(self.btn_import_xml)
        # header_frame.addWidget(self.message_label)
        #
        # header_container = QWidget(self)
        # header_container.setLayout(header_frame)
        # layout.addWidget(header_container)

        # Order card
        layout.addWidget(self.order_card)

        # Footer frame
        footer_frame = QHBoxLayout()
        footer_frame.addWidget(self.btn_save)
        footer_frame.addStretch()
        footer_frame.addWidget(self.btn_close)

        footer_container = QWidget(self)
        footer_container.setLayout(footer_frame)
        layout.addWidget(footer_container)

        # ── Signal Connections ────────────────────────────────────────
        self.order_card.order_changed.connect(self._on_card_changed)
        # self.btn_import_xml.clicked.connect(self._on_import_xml)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_close.clicked.connect(self.reject)

    def _on_import_xml(self) -> None:
        """Handle XML import button click."""
        file_path: str = QFileDialog.getOpenFileName(
            self, "Importar XML", "", "Arquivos XML (*.xml)"
        )[0]
        if not file_path:
            return

        result = import_xml(file_path)
        if result.get("orders"):
            self.order_card.set_order_data(result["orders"][0])
            if result.get("warnings"):
                self._show_message(
                    "Importação concluída com avisos: " + " ".join(result["warnings"]),
                    "warning",
                )
            else:
                self._show_message("XML importado com sucesso.", "success")
        else:
            self._show_message("Nenhum pedido encontrado no arquivo XML.", "error")

    def _on_save(self) -> None:
        """Handle save button click."""
        # Validate
        valid, errors = self.order_card.validate()
        if not valid:
            self._show_message("Há campos inválidos: " + "; ".join(errors), "error")
            return

        # Collect order data
        order_data: OrderInputDict = self.order_card.get_order_data()  # type: ignore[union-attr]

        # Determine deleted order IDs
        deleted_ids: list[str] = []
        if not self.order_card._is_new:
            deleted_ids = [self.order_card._order_id]

        # Save
        success: bool = save_orders([order_data], deleted_ids)
        if success:
            self._show_message("Salvo com sucesso!", "success")
            self.order_saved.emit(order_data)
            self.accept()
        else:
            self._show_message("Erro ao salvar pedido.", "error")

    def _on_card_changed(self) -> None:
        """Update footer total and distribute button state on card changes."""
        total_cents: int = self.order_card.get_products_total()
        self.order_card.products_total_label.setText(
            f"Total dos produtos: {cents_to_display(total_cents)}"
        )

        # Enable/disable distribute button
        valid, _ = self.order_card.validate()
        can_distribute: bool = valid and total_cents > 0
        self.order_card.distribute_button.setEnabled(can_distribute)

    def _show_message(self, text: str, level: str) -> None:
        """Show a styled message in the message label, auto-clear after 5 seconds."""
        colors: dict[str, str] = {
            "success": "background-color: #d4edda; color: #155724;",
            "error": "background-color: #f8d7da; color: #721c24;",
            "warning": "background-color: #fff3cd; color: #856404;",
        }
        self.message_label.setText(text)
        self.message_label.setStyleSheet(colors.get(level, ""))
        QTimer.singleShot(5000, self.message_label.clear)  # type: ignore[union-attr]
