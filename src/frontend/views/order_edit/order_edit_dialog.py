from __future__ import annotations

import uuid
from datetime import date

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from backend import OrderInput
from backend.utils.currency import cents_to_display
from models.order import Order
from bridge.order import fetch_order_by_id, save_single_order
from frontend.views.order_edit.order_header_card import OrderHeaderCard
from frontend.views.order_edit.order_items_card import OrderItemsCard


class OrderEditDialog(QDialog):
    """Modal dialog for editing a single order."""

    order_saved: Signal = Signal(object)
    closed: Signal = Signal()
    _was_validated = False

    def __init__(
            self,
            parent: QWidget | None = None,
            order_id: str | None = None,
            order: Order | None = None,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumSize(800, 600)

        # ── Header Card ───────────────────────────────────────────────
        self.header_card: OrderHeaderCard = OrderHeaderCard(self)

        # ── Items Card ────────────────────────────────────────────────
        self.items_card: OrderItemsCard = OrderItemsCard(self)

        # ── State ─────────────────────────────────────────────────────
        if order is not None:
            # XML import path: order already parsed
            self._imported_order: Order = order
            self._order_id: str = order.id
            self._is_new: bool = True
            self.header_card.set_order_data(order)
            self.items_card.set_order_data(order)
        elif order_id:
            # Existing edit path: fetch from DB
            order_data: Order | None = fetch_order_by_id(order_id)
            self._order_id: str = order_data.id if order_data else str(uuid.uuid4())
            self._is_new: bool = order_data is None
            if order_data is not None:
                self.header_card.set_order_data(order_data)
                self.items_card.set_order_data(order_data)
            else:
                self.items_card.add_row()
        else:
            # Blank new order path
            self._order_id: str = str(uuid.uuid4())
            self._is_new: bool = True
            self.items_card.add_row()

        self.setWindowTitle("Novo Pedido" if self._is_new else "Editar Pedido")

        # ── Footer Buttons ────────────────────────────────────────────
        self.btn_save: QPushButton = QPushButton("Salvar", self)
        self.btn_save.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.btn_close: QPushButton = QPushButton("Fechar", self)
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # ── Main Layout ───────────────────────────────────────────────
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        # Header card (no stretch)
        layout.addWidget(self.header_card)

        # Items card (stretch = 1, takes remaining space)
        layout.addWidget(self.items_card, 1)

        # Message label
        self.message_label: QLabel = QLabel(self)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        # Footer frame
        footer_frame = QHBoxLayout()
        footer_frame.addWidget(self.btn_save)
        footer_frame.addStretch()
        footer_frame.addWidget(self.btn_close)

        footer_container = QWidget(self)
        footer_container.setLayout(footer_frame)
        layout.addWidget(footer_container)

        # ── Signal Connections ────────────────────────────────────────
        self.header_card.order_changed.connect(self.header_card.order_changed)
        self.items_card.order_changed.connect(self.items_card.order_changed)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_close.clicked.connect(self.reject)

    def _on_save(self) -> None:
        """Handle save button click."""
        self._was_validated = True
        # Validate header
        header_valid, header_errors = self.header_card.validate()
        # Validate items
        items_valid, items_errors = self.items_card.validate(show_errors=True)

        if not (header_valid and items_valid):
            return

        # Preserve nfe_key from XML-imported orders
        nfe_key: str = ""
        if hasattr(self, "_imported_order") and self._imported_order is not None:
            nfe_key = self._imported_order.nfe_key

        # Assemble full order data from both cards
        order_data = OrderInput(
            id=self._order_id,
            date=date.strptime(self.header_card.get_date(), "%d/%m/%Y"),
            supplier=self.header_card.get_supplier(),
            nfe_key=nfe_key,
            freight=self.header_card.get_freight_cents(),
            unloading=self.header_card.get_unloading_cents(),
            products=self.items_card.get_products_list(self._order_id),
        )

        # Save
        success: bool = save_single_order(order_data)
        if success:
            self._show_message("Salvo com sucesso!", "success")
            self.order_saved.emit(order_data)
            self.accept()
        else:
            self._show_message("Erro ao salvar pedido.", "error")

    def _show_message(self, text: str, level: str) -> None:
        """Show a styled message in the message label, auto-clear after 5 seconds."""
        colors: dict[str, str] = {
            "success": "background-color: #d4edda; color: #155724;",
            "error": "background-color: #f8d7da; color: #721c24;",
            "warning": "background-color: #fff3cd; color: #856404;",
        }
        self.message_label.setText(text)
        self.message_label.setStyleSheet(colors.get(level, ""))
        QTimer.singleShot(5000, self.message_label.clear)
