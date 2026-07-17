from __future__ import annotations

import uuid
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bridge.models.order import OrderDict, OrderInputDict
from bridge.models.product import ProductDict
from frontend.business import distribute_freight, validate_order
from frontend.product_row_widget import ProductRowWidget
from backend.utils.currency import cents_to_display, parse_currency_to_cents
from backend.utils.date import br_date_to_iso, iso_to_br_date


class OrderCardWidget(QWidget):
    """A single order card with header fields, product rows container, and footer."""

    order_changed: Signal = Signal()

    def __init__(
            self,
            parent: QWidget | None = None,
            order_data: OrderDict | None = None,
    ) -> None:
        super().__init__(parent)

        # State
        self._order_id: str = order_data["id"] if order_data else str(uuid.uuid4())
        self._is_new: bool = order_data is None

        # ── Header ────────────────────────────────────────────────────
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
        header_layout.setSpacing(10)

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

        # ── Product Rows Container ────────────────────────────────────
        self.products_layout: QVBoxLayout = QVBoxLayout()
        self.products_layout.setSpacing(0)
        self.products_layout.setContentsMargins(0, 0, 0, 0)
        self._product_rows: list[ProductRowWidget] = []

        # ── Footer ────────────────────────────────────────────────────
        self.products_total_label: QLabel = QLabel(
            "Total dos produtos: R$ 0,00", self
        )
        self.distribute_button: QPushButton = QPushButton(
            "Distribuir frete", self
        )
        self.distribute_button.setDisabled(True)

        footer_layout: QHBoxLayout = QHBoxLayout()
        footer_layout.addWidget(self.products_total_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.distribute_button)

        # ── Main Layout ───────────────────────────────────────────────
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addLayout(header_layout)
        main_layout.addLayout(self.products_layout)
        main_layout.addLayout(footer_layout)

        # ── Signal Connections ────────────────────────────────────────
        self.supplier_input.textChanged.connect(self._on_header_changed)
        self.date_input.textChanged.connect(self._on_header_changed)
        self.freight_input.textChanged.connect(self._on_header_changed)
        self.unloading_input.textChanged.connect(self._on_header_changed)
        self.distribute_button.clicked.connect(self._on_distribute_freight)

        # ── Initialize Product Rows ───────────────────────────────────
        if order_data is not None:
            self._set_from_order_data(order_data)
        else:
            # Fresh order: add one empty row
            self._add_empty_row()

    # ── Header Change Handling ──────────────────────────────────────

    def _on_header_changed(self) -> None:
        """Emit order_changed when any header field changes."""
        self.order_changed.emit()

    # ── Product Row Management ──────────────────────────────────────

    def _add_empty_row(self) -> ProductRowWidget:
        """Add a new empty product row to the layout."""
        row = ProductRowWidget(self)
        self._product_rows.append(row)
        self.products_layout.addWidget(row)
        row.row_changed.connect(self._on_row_changed)
        self._update_delete_buttons()
        return row

    def _on_row_changed(self) -> None:
        """Handle changes in a product row: auto-add or auto-remove."""
        changed_row: ProductRowWidget = self.sender()  # type: ignore[union-attr]
        row_index: int = self._product_rows.index(changed_row)

        # Auto-remove: if non-last row becomes empty
        if row_index < len(self._product_rows) - 1 and changed_row.is_empty():
            self.products_layout.removeWidget(changed_row)
            changed_row.deleteLater()
            self._product_rows.pop(row_index)
            self._update_delete_buttons()
            self.order_changed.emit()
            return

        # Auto-add: if the last row is filled (not empty), add a new empty row
        last_row = self._product_rows[-1]
        if not last_row.is_empty() and changed_row is last_row:
            new_row = self._add_empty_row()
            self.order_changed.emit()

    def _update_delete_buttons(self) -> None:
        """Enable delete button only for non-last rows."""
        for i, row in enumerate(self._product_rows):
            row.delete_button.setEnabled(i < len(self._product_rows) - 1)

    # ── Freight Distribution ────────────────────────────────────────

    def _on_distribute_freight(self) -> None:
        """Distribute freight/unloading costs across product prices."""
        order_data: OrderInputDict = self.get_order_data()
        result = distribute_freight(order_data)
        if result and result.get("new_products"):
            new_products: list[ProductDict] = result["new_products"]
            for i, new_product in enumerate(new_products):
                if i < len(self._product_rows):
                    self._product_rows[i].price_input.setText(
                        cents_to_display(new_product["price"])
                    )
            self.order_changed.emit()

    # ── Data Access ─────────────────────────────────────────────────

    def get_order_data(self) -> OrderInputDict:
        """Collect all fields + products into a save-ready dict."""
        return {
            "id": self._order_id,
            "date": self.date_input.text().strip(),
            "supplier": self.supplier_input.text().strip(),
            "nfeKey": self.nfe_key_input.text().strip(),
            "freight": parse_currency_to_cents(self.freight_input.text()),
            "unloading": parse_currency_to_cents(self.unloading_input.text()),
            "products": [
                row.get_product_data(self._order_id, i)
                for i, row in enumerate(self._product_rows)
            ],
        }

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate header + all product rows.
        Returns (True, []) if valid, (False, [errors]) if invalid.
        """
        errors: list[str] = []

        # Validate header
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

        # Validate each product
        for i, row in enumerate(self._product_rows):
            valid, row_errors = row.validate()
            if not valid:
                for err in row_errors:
                    errors.append(f"Produto {i + 1}: {err}")

        return (len(errors) == 0, errors)

    def get_products_total(self) -> int:
        """Sum of all product totals in cents."""
        return sum(
            parse_currency_to_cents(row.total_input.text())
            for row in self._product_rows
        )

    # ── Data Loading ────────────────────────────────────────────────

    def _set_from_order_data(self, order_data: OrderDict) -> None:
        """Pre-fill from an existing order dict."""
        self._order_id = order_data["id"]
        self._is_new = False
        self.supplier_input.setText(order_data.get("supplier", ""))
        self.date_input.setText(iso_to_br_date(order_data["date"]))
        self.nfe_key_input.setText(order_data.get("nfeKey", ""))
        self.freight_input.setText(cents_to_display(order_data["freight"]))
        self.unloading_input.setText(cents_to_display(order_data["unloading"]))

        # Replace all product rows
        for row in self._product_rows:
            self.products_layout.removeWidget(row)
            row.deleteLater()
        self._product_rows.clear()

        for product in order_data["products"]:
            row = ProductRowWidget(self, product_data=product)
            self._product_rows.append(row)
            self.products_layout.addWidget(row)
            row.row_changed.connect(self._on_row_changed)

        self._update_delete_buttons()
        self.order_changed.emit()

    def set_order_data(self, order_data: OrderDict) -> None:
        """Pre-fill from an existing order dict (public API, same as _set_from_order_data)."""
        self._set_from_order_data(order_data)

    def clear(self) -> None:
        """Clear all fields and add one empty product row (for XML import replacement)."""
        self.supplier_input.clear()
        self.date_input.clear()
        self.nfe_key_input.clear()
        self.freight_input.clear()
        self.unloading_input.clear()

        # Remove all product rows and add one empty
        for row in self._product_rows:
            self.products_layout.removeWidget(row)
            row.deleteLater()
        self._product_rows.clear()

        new_row = self._add_empty_row()
        self.order_changed.emit()
