from __future__ import annotations

import uuid

from PySide6.QtCore import Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bridge.models.product import ProductDict
from backend.utils.currency import cents_to_display, parse_currency_to_cents


class ProductRowWidget(QWidget):
    """A single product entry row with name, quantity, price, total (read-only), and delete button."""

    row_changed: Signal = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        product_data: ProductDict | None = None,
    ) -> None:
        super().__init__(parent)
        self._id: str = product_data["id"] if product_data else str(uuid.uuid4())

        # Name input
        self.name_input: QLineEdit = QLineEdit(self)
        self.name_input.setPlaceholderText("Produto")

        # Quantity input — digits only
        self.quantity_input: QLineEdit = QLineEdit(self)
        self.quantity_input.setPlaceholderText("Qtde")
        qty_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            r"^\d*$"
        )
        self.quantity_input.setValidator(qty_validator)

        # Price input — currency format
        self.price_input: QLineEdit = QLineEdit(self)
        self.price_input.setPlaceholderText("R$ 0,00")
        price_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            r"^\d*([.,]\d{1,2})?$"
        )
        self.price_input.setValidator(price_validator)

        # Total input — read-only, gray
        self.total_input: QLineEdit = QLineEdit(self)
        self.total_input.setPlaceholderText("R$ 0,00")
        self.total_input.setReadOnly(True)
        self.total_input.setStyleSheet("color: gray;")

        # Delete button
        self.delete_button: QPushButton = QPushButton("✕", self)
        self.delete_button.setFixedSize(28, 28)

        # Layout
        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.name_input)
        layout.addWidget(self.quantity_input)
        layout.addWidget(self.price_input)
        layout.addWidget(self.total_input)
        layout.addWidget(self.delete_button)

        # Signal connections for auto-calculation
        self.price_input.textChanged.connect(self._recalculate_total)
        self.quantity_input.textChanged.connect(self._recalculate_total)
        self.name_input.textChanged.connect(self._on_any_changed)
        self.delete_button.clicked.connect(self._on_delete)

        # Pre-fill if product_data provided
        if product_data is not None:
            self.name_input.setText(product_data.get("name", ""))
            self.quantity_input.setText(str(product_data.get("quantity", 0)))
            self.price_input.setText(cents_to_display(product_data.get("price", 0)))
            self.total_input.setText(cents_to_display(product_data.get("total", 0)))

        # Initial total calculation
        self._recalculate_total()

    def _recalculate_total(self) -> None:
        """Auto-calculate total from price × quantity."""
        price_cents: int = parse_currency_to_cents(self.price_input.text())
        quantity_text: str = self.quantity_input.text().strip()
        quantity: int = int(quantity_text) if quantity_text else 0
        total_cents: int = price_cents * quantity
        self.total_input.setText(cents_to_display(total_cents))

    def _on_any_changed(self) -> None:
        """Emit row_changed signal whenever any field changes."""
        self.row_changed.emit()

    def _on_delete(self) -> None:
        """Handle delete button click."""
        pass

    def is_empty(self) -> bool:
        """Return True if name is empty AND quantity is 0 AND price is 0."""
        return (
            not self.name_input.text().strip()
            and not self.quantity_input.text().strip()
            and not self.price_input.text().strip()
        )

    def get_product_data(
        self, order_id: str, item_ordinal: int | None = None
    ) -> ProductDict:
        """Return a ProductDict from the current widget state."""
        return {
            "id": self._id,
            "name": self.name_input.text().strip(),
            "quantity": int(self.quantity_input.text())
            if self.quantity_input.text().strip()
            else 0,
            "price": parse_currency_to_cents(self.price_input.text()),
            "total": parse_currency_to_cents(self.total_input.text()),
            "order_id": order_id,
            "itemOrdinal": item_ordinal,
        }

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the row using requiredIfFilled logic.
        If any of name/quantity/price is filled, all three must be filled.
        Returns (True, []) if valid or fully empty; (False, [errors]) if partially filled.
        """
        name: str = self.name_input.text().strip()
        quantity_text: str = self.quantity_input.text().strip()
        price_text: str = self.price_input.text().strip()

        name_filled: bool = bool(name)
        qty_filled: bool = quantity_text != ""
        price_filled: bool = bool(price_text)

        filled_count: int = sum([name_filled, qty_filled, price_filled])

        if 0 < filled_count < 3:
            errors: list[str] = []
            if not name_filled:
                errors.append(
                    "Nome do produto obrigatório quando outros campos estão preenchidos."
                )
            if not qty_filled:
                errors.append(
                    "Quantidade do produto obrigatória quando outros campos estão preenchidos."
                )
            if not price_filled:
                errors.append(
                    "Preço do produto obrigatório quando outros campos estão preenchidos."
                )
            return False, errors

        return True, []
