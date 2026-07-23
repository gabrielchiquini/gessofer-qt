from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from bridge.models.order import OrderDict
from frontend.components.card import Card
from frontend.components.text_field import TextField
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
        self.supplier_input: TextField = TextField(
            self,
            label="Fornecedor",
            placeholder="Fornecedor",
            required=True,
        )
        self.supplier_input.setMinimumWidth(180)

        self.date_input: TextField = TextField(
            self,
            label="Data",
            placeholder="DD/MM/AAAA",
            input_mask="99/99/9999",
            required=True,
        )

        self.freight_input: TextField = TextField(
            self,
            label="Frete",
            placeholder="R$ 0,00",
            regex_validation_pattern=r"^\d*([.,]\d{1,2})?$",
        )

        self.unloading_input: TextField = TextField(
            self,
            label="Descarga",
            placeholder="R$ 0,00",
            regex_validation_pattern=r"^\d*([.,]\d{1,2})?$",
        )

        # Header layout — TextField widgets (each has its own label internally)
        header_layout: QHBoxLayout = QHBoxLayout()

        header_layout.addWidget(self.supplier_input)
        header_layout.addWidget(self.date_input)
        header_layout.addWidget(self.freight_input)
        header_layout.addWidget(self.unloading_input)

        self._card.set_content(header_layout)

        # ── Signal Connections ────────────────────────────────────────
        self.supplier_input.connect_text_changed(self._on_header_changed)
        self.date_input.connect_text_changed(self._on_header_changed)
        self.freight_input.connect_text_changed(self._on_header_changed)
        self.unloading_input.connect_text_changed(self._on_header_changed)

        # ── Main Layout ───────────────────────────────────────────────
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._card)

    # ── Header Change Handling ──────────────────────────────────────

    def _on_header_changed(self, _: str) -> None:
        """Emit order_changed when any header field changes."""
        self.order_changed.emit()

    # ── Data Access ─────────────────────────────────────────────────

    def get_supplier(self) -> str:
        """Return the supplier text."""
        return self.supplier_input.get_text().strip()

    def get_date(self) -> str:
        """Return the date text."""
        return self.date_input.get_text().strip()

    def get_freight_cents(self) -> int:
        """Return freight value in cents."""
        return parse_currency_to_cents(self.freight_input.get_text())

    def get_unloading_cents(self) -> int:
        """Return unloading value in cents."""
        return parse_currency_to_cents(self.unloading_input.get_text())

    def set_supplier(self, text: str) -> None:
        """Set the supplier text."""
        self.supplier_input.set_text(text)

    def set_date_br(self, text: str) -> None:
        """Set the date in BR format (dd/MM/yyyy)."""
        self.date_input.set_text(text)

    def set_freight_cents(self, cents: int) -> None:
        """Set the freight value from cents."""
        self.freight_input.set_text(cents_to_display(cents))

    def set_unloading_cents(self, cents: int) -> None:
        """Set the unloading value from cents."""
        self.unloading_input.set_text(cents_to_display(cents))

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
        Validate supplier and date format.
        Returns (True, []) if valid, (False, [errors]) if not.
        """
        errors: list[str] = []

        # Supplier validation (TextField handles required)
        supplier_valid, supplier_error = self.supplier_input.validate()
        if not supplier_valid:
            errors.append(supplier_error)

        # Date semantic validation
        date_text: str = self.date_input.get_text().strip()
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

        return len(errors) == 0, errors
