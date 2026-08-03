from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from backend.utils.currency import cents_to_display, parse_currency_to_cents
from backend.utils.date import iso_to_br_date
from bridge.models.order import Order
from frontend.components.card import Card
from frontend.components.text_field import TextField
from frontend.util.validators import DateValidator


class OrderHeaderCard(QWidget):
    """Header card for order editing: supplier, date, freight, unloading."""

    order_changed: Signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # ── Card Container ────────────────────────────────────────────
        self._card: Card = Card(self)
        self._card.set_title("Dados do pedido")

        # ── Header Fields ─────────────────────────────────────────────
        self._supplier_input: TextField = TextField(
            self,
            label="Fornecedor",
            placeholder="Fornecedor",
            required=True,
        )
        self._supplier_input.setMinimumWidth(180)

        self._date_input: TextField = TextField(
            self,
            label="Data",
            placeholder="DD/MM/AAAA",
            input_mask="99/99/9999",
            required=True,
            custom_validator=DateValidator(self),
            custom_error_message="Data inválida",
        )

        self._freight_input: TextField = TextField(
            self,
            label="Frete",
            placeholder="R$ 0,00",
            regex_validation_pattern=r"^\d*([.,]\d{1,2})?$",
        )

        self._unloading_input: TextField = TextField(
            self,
            label="Descarga",
            placeholder="R$ 0,00",
            regex_validation_pattern=r"^\d*([.,]\d{1,2})?$",
        )

        # Header layout — TextField widgets (each has its own label internally)
        header_layout: QHBoxLayout = QHBoxLayout()

        header_layout.addWidget(self._supplier_input)
        header_layout.addWidget(self._date_input)
        header_layout.addWidget(self._freight_input)
        header_layout.addWidget(self._unloading_input)

        self._card.set_content(header_layout)

        # ── Signal Connections ────────────────────────────────────────
        self._supplier_input.connect_text_changed(self._on_header_changed)
        self._date_input.connect_text_changed(self._on_header_changed)
        self._freight_input.connect_text_changed(self._on_header_changed)
        self._unloading_input.connect_text_changed(self._on_header_changed)

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
        return self._supplier_input.get_text().strip()

    def get_date(self) -> str:
        """Return the date text."""
        return self._date_input.get_text().strip()

    def get_freight_cents(self) -> int:
        """Return freight value in cents."""
        return parse_currency_to_cents(self._freight_input.get_text())

    def get_unloading_cents(self) -> int:
        """Return unloading value in cents."""
        return parse_currency_to_cents(self._unloading_input.get_text())

    def set_order_data(self, order_data: Order) -> None:
        """Load all four fields from an Order dataclass."""
        self._supplier_input.set_text(order_data.supplier)
        self._date_input.set_text(iso_to_br_date(order_data.date))
        cents1 = order_data.freight
        if cents1 > 0:
            self._freight_input.set_text(cents_to_display(cents1))
        cents = order_data.unloading
        if cents > 0:
            self._unloading_input.set_text(cents_to_display(cents))
        self.order_changed.emit()

    def clear(self) -> None:
        """Clear all four fields."""
        self._supplier_input.clear()
        self._date_input.clear()
        self._freight_input.clear()
        self._unloading_input.clear()

    def validate(self) -> tuple[bool, list[str]]:
        """Validate supplier (required) and return any errors.

        Date format and semantics are enforced by the ``DateValidator``
        attached to ``date_input`` via the ``TextField``.

        Returns (True, []) if valid, (False, [errors]) if not.
        """
        errors: list[str] = []

        # Supplier validation (TextField handles required)
        supplier_valid, supplier_error = self._supplier_input.validate()
        if not supplier_valid:
            errors.append(supplier_error)

        # Date validation (TextField handles format + semantics)
        date_valid, date_error = self._date_input.validate()
        if not date_valid:
            errors.append(date_error)

        return len(errors) == 0, errors
