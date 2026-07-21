from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from bridge.models.order import OrderDict
from frontend.components.card import Card
from backend.utils.currency import cents_to_display, parse_currency_to_cents
from backend.utils.date import iso_to_br_date


class OrderHeaderCard(QWidget):
    """Header card for order editing: supplier, date, freight, unloading."""

    order_changed: Signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # ── Card Container ────────────────────────────────────────────
        self._card: Card = Card(self)
        self._card.set_title("Dados do pedido")

        # ── Header Fields ─────────────────────────────────────────────
        self.supplier_input: QLineEdit = QLineEdit(self)
        self.supplier_input.setPlaceholderText("Fornecedor")
        self.supplier_input.setMinimumWidth(180)

        self.date_input: QLineEdit = QLineEdit(self)
        self.date_input.setInputMask("99/99/9999")
        self.date_input.setPlaceholderText("DD/MM/AAAA")

        self.freight_input: QLineEdit = QLineEdit(self)
        self.freight_input.setPlaceholderText("R$ 0,00")
        freight_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            r"^\d*([.,]\d{1,2})?$"
        )
        self.freight_input.setValidator(freight_validator)

        self.unloading_input: QLineEdit = QLineEdit(self)
        self.unloading_input.setPlaceholderText("R$ 0,00")
        unloading_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            r"^\d*([.,]\d{1,2})?$"
        )
        self.unloading_input.setValidator(unloading_validator)

        # Header layout — vertical label/input pairs
        header_layout: QHBoxLayout = QHBoxLayout()

        # Fornecedor
        _col_fornecedor: QVBoxLayout = QVBoxLayout()
        _col_fornecedor.setSpacing(0)
        _col_fornecedor.addWidget(QLabel("Fornecedor:", self))
        _col_fornecedor.addWidget(self.supplier_input)
        header_layout.addLayout(_col_fornecedor)

        # Data
        _col_data: QVBoxLayout = QVBoxLayout()
        _col_data.setSpacing(0)
        _col_data.addWidget(QLabel("Data:", self))
        _col_data.addWidget(self.date_input)
        header_layout.addLayout(_col_data)

        # Frete
        _col_frete: QVBoxLayout = QVBoxLayout()
        _col_frete.setSpacing(0)
        _col_frete.addWidget(QLabel("Frete:", self))
        _col_frete.addWidget(self.freight_input)
        header_layout.addLayout(_col_frete)

        # Descarga
        _col_descarga: QVBoxLayout = QVBoxLayout()
        _col_descarga.setSpacing(0)
        _col_descarga.addWidget(QLabel("Descarga:", self))
        _col_descarga.addWidget(self.unloading_input)
        header_layout.addLayout(_col_descarga)

        self._card.set_content(header_layout)

        # ── Signal Connections ────────────────────────────────────────
        self.supplier_input.textChanged.connect(self._on_header_changed)
        self.date_input.textChanged.connect(self._on_header_changed)
        self.freight_input.textChanged.connect(self._on_header_changed)
        self.unloading_input.textChanged.connect(self._on_header_changed)

        # ── Main Layout ───────────────────────────────────────────────
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._card)

    # ── Header Change Handling ──────────────────────────────────────

    def _on_header_changed(self) -> None:
        """Emit order_changed when any header field changes."""
        self.order_changed.emit()

    # ── Data Access ─────────────────────────────────────────────────

    def get_supplier(self) -> str:
        """Return the supplier text."""
        return self.supplier_input.text().strip()

    def get_date(self) -> str:
        """Return the date text."""
        return self.date_input.text().strip()

    def get_freight_cents(self) -> int:
        """Return freight value in cents."""
        return parse_currency_to_cents(self.freight_input.text())

    def get_unloading_cents(self) -> int:
        """Return unloading value in cents."""
        return parse_currency_to_cents(self.unloading_input.text())

    def set_supplier(self, text: str) -> None:
        """Set the supplier text."""
        self.supplier_input.setText(text)

    def set_date_br(self, text: str) -> None:
        """Set the date in BR format (dd/MM/yyyy)."""
        self.date_input.setText(text)

    def set_freight_cents(self, cents: int) -> None:
        """Set the freight value from cents."""
        self.freight_input.setText(cents_to_display(cents))

    def set_unloading_cents(self, cents: int) -> None:
        """Set the unloading value from cents."""
        self.unloading_input.setText(cents_to_display(cents))

    def set_order_data(self, order_data: OrderDict) -> None:
        """Load all four fields from an OrderDict."""
        self.set_supplier(order_data.get("supplier", ""))
        self.set_date_br(iso_to_br_date(order_data["date"]))
        self.set_freight_cents(order_data["freight"])
        self.set_unloading_cents(order_data["unloading"])
        self.order_changed.emit()

    def clear(self) -> None:
        """Clear all four fields."""
        self.supplier_input.clear()
        self.date_input.clear()
        self.freight_input.clear()
        self.unloading_input.clear()

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate date format and supplier required.
        Returns (True, []) if valid, (False, [errors]) if not.
        """
        errors: list[str] = []

        date_text: str = self.date_input.text().strip()
        supplier_text: str = self.supplier_input.text().strip()

        if not date_text:
            errors.append("Data do pedido obrigatória.")
        else:
            parts: list[str] = date_text.split("/")
            if len(parts) != 3:
                errors.append(
                    f"Formato de data inválido: '{date_text}'. Use DD/MM/AAAA."
                )
            else:
                try:
                    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                    if not (1 <= d <= 31 and 1 <= m <= 12 and y >= 1900):
                        errors.append(f"Data inválida: '{date_text}'.")
                except ValueError:
                    errors.append(
                        f"Formato de data inválido: '{date_text}'. Use DD/MM/AAAA."
                    )

        if not supplier_text:
            errors.append("Fornecedor obrigatório.")

        return (len(errors) == 0, errors)
