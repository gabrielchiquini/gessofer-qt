from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from backend.utils.currency import cents_to_display, parse_currency_to_cents
from frontend.components.card import Card
from frontend.views.order_edit.product_row_widget import ProductRowWidget
from models.input import ProductInput
from models.output import Product


class OrderItemsCard(QWidget):
    """Items card for order editing: product rows, total, and freight distribution."""

    order_changed: Signal = Signal()
    row_added: Signal = Signal(ProductRowWidget)

    def __init__(
            self,
            parent: QWidget,
    ) -> None:
        super().__init__(parent)
        # ── Card Container ────────────────────────────────────────────
        self._card: Card = Card(self)
        self._card.set_title("Itens")

        # ── Product Rows Container ────────────────────────────────────
        self.products_layout: QVBoxLayout = QVBoxLayout()
        self.products_layout.setSpacing(0)
        self.products_layout.setContentsMargins(0, 0, 0, 0)
        self.products_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._product_rows: list[ProductRowWidget] = []

        # ── Scroll Area for Product Rows ────────────────────────────────
        self._scroll_container: QWidget = QWidget()
        self._scroll_container.setContentsMargins(0, 0, 0, 0)
        self._scroll_container.setObjectName("scroll_container")
        self._scroll_container.setStyleSheet(
            "#scroll_container { background-color: white; border: 0px; border-radius: 0px; }")
        self._scroll_container.setLayout(self.products_layout)

        self._scroll_area: QScrollArea = QScrollArea(self)
        self._scroll_area.setWidget(self._scroll_container)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self._card.set_content(self._scroll_area)

        # ── Footer ────────────────────────────────────────────────────
        self._products_total_label: QLabel = QLabel(
            "Total dos produtos: 0,00", self
        )

        footer_layout: QHBoxLayout = QHBoxLayout()
        footer_layout.addWidget(self._products_total_label)
        footer_layout.addStretch()

        self._card.build_footer()
        self._card.set_footer(footer_layout)

        # ── Signal Connections ────────────────────────────────────────

        # ── Main Layout ───────────────────────────────────────────────
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(self._card)

    # ── Product Row Management ──────────────────────────────────────

    def _add_empty_row(self) -> ProductRowWidget:
        """Add a new empty product row to the layout."""
        row = self.setup_row()
        self._update_delete_buttons()
        self.row_added.emit(row)
        return row

    def _on_row_changed(self) -> None:
        """Handle changes in a product row: auto-add or auto-remove."""
        changed_row: ProductRowWidget = self.sender()  # type: ignore[union-attr]
        changed_row.validate()

        # Auto-add: if the last row is filled (not empty), add a new empty row
        last_row = self._product_rows[-1]
        if not last_row.is_empty() and changed_row is last_row:
            new_row = self._add_empty_row()
        self._order_changed()

    def _update_delete_buttons(self) -> None:
        """Enable delete button only for non-last rows."""
        for i, row in enumerate(self._product_rows):
            row.delete_button.setEnabled(i < len(self._product_rows) - 1)

    # ── Freight Distribution ────────────────────────────────────────

    def set_freight_data(self, freight_cents: int, unloading_cents: int) -> None:
        """Update freight/unloading and recalculate price_with_freight for all rows."""
        if not self._product_rows:
            return

        products_total: int = sum(
            parse_currency_to_cents(row.total_input.text())
            for row in self._product_rows
        )
        if products_total == 0:
            # No products — reset all to just the base price
            for row in self._product_rows:
                base_price: int = parse_currency_to_cents(row.price_input.text())
                row.set_price_with_freight(base_price)
            return

        freight_total: int = freight_cents + unloading_cents
        ratio: float = (freight_total + products_total) / products_total

        for row in self._product_rows:
            base_price: int = parse_currency_to_cents(row.price_input.text())
            quantity: int = int(row.quantity_input.text()) if row.quantity_input.text().strip() else 0
            if quantity == 0:
                # Avoid division by zero — keep original price
                pwf: int = base_price
            else:
                # Same algorithm as FreightDistributionService:
                # new_price = round((total * ratio) / quantity)
                # where total = base_price * quantity
                product_total: int = base_price * quantity
                pwf = round((product_total * ratio) / quantity)
            row.set_price_with_freight(pwf)

    def get_products_total(self) -> int:
        """Sum of all product totals in cents."""
        return sum(
            parse_currency_to_cents(row.total_input.text())
            for row in self._product_rows
        )

    # ── Data Access ─────────────────────────────────────────────────

    def get_products_list(self, order_id: str = "") -> list[ProductInput]:
        """Return a list of ProductInput from all product rows."""
        return [
            row.get_product_data(order_id, i) for i, row in enumerate(self._product_rows[:-1])  # ignores last empty row
        ]

    def validate(self, *, show_errors: bool = False) -> tuple[bool, list[str]]:
        """
        Validate each product row.
        Returns combined results: (True, []) if all valid, (False, [errors]) if any invalid.
        """
        errors: list[str] = []
        for i, row in enumerate(self._product_rows):
            valid, row_errors = row.validate(show_errors=show_errors)
            if not valid:
                for err in row_errors:
                    errors.append(f"Produto {i + 1}: {err}")
        return len(errors) == 0, errors

    def set_order_data(self, products: list[Product]) -> None:
        """Replace product rows with those from order_data."""
        # Remove all existing rows
        for row in self._product_rows:
            self.products_layout.removeWidget(row)
            row.deleteLater()
        self._product_rows.clear()

        # Add rows from order data
        for product in products:
            row = self.setup_row(product=product)
            if hasattr(product, "warnings") and product.warnings:
                row.set_warnings(product.warnings)
        self._add_empty_row()

        self._update_delete_buttons()
        self._order_changed()

    # ── Data Loading ────────────────────────────────────────────────

    def setup_row(self, *, product: Product | None = None):
        row = ProductRowWidget(self, product_data=product)
        self._product_rows.append(row)
        self.products_layout.addWidget(row)
        row.row_changed.connect(self._on_row_changed)
        row.delete_pressed.connect(self.delete_row)
        return row

    def add_row(self) -> ProductRowWidget:
        """Public method to add a row (for XML import or other callers)."""
        return self._add_empty_row()

    def delete_row(self):
        row: ProductRowWidget = self.sender()  # type: ignore[union-attr]
        row.deleteLater()
        self.products_layout.removeWidget(row)
        index = self._product_rows.index(row)
        self._product_rows.pop(index)
        self._update_delete_buttons()
        self._order_changed()

    def get_product_rows(self) -> list[ProductRowWidget]:
        """Return the _product_rows list (for external access if needed)."""
        return self._product_rows

    def _order_changed(self):
        total_cents: int = self.get_products_total()
        self._products_total_label.setText(
            f"Total dos produtos: {cents_to_display(total_cents)}"
        )
        self.order_changed.emit()
