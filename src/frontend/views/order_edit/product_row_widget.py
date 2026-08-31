from __future__ import annotations

import uuid

from PySide6.QtCore import Signal, Qt, QEvent, QPoint, QObject
from PySide6.QtGui import QRegularExpressionValidator, QFont, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget, )

from backend.utils.currency import cents_to_input, parse_currency_to_cents
from frontend.util.icons import svg_to_pixmap
from models.input import ProductInput
from models.output import Product
from util.paths import ASSETS_DIR

_EXCLAMATION_ICON_PATH = str(ASSETS_DIR / "circle-exclamation.svg")
_EXCLAMATION_ICON: QIcon = QIcon(_EXCLAMATION_ICON_PATH)


class ProductRowWidget(QWidget):
    """A single product entry row with name, quantity, price, total (read-only), and delete button."""

    row_changed: Signal = Signal()
    delete_pressed: Signal = Signal()

    def __init__(
            self,
            parent: QWidget | None = None,
            product_data: Product | None = None,
    ) -> None:
        super().__init__(parent)
        self.hover_filter = None
        self._id: str = product_data.id if product_data else str(uuid.uuid4())

        # Name input
        self._name_input: QLineEdit = QLineEdit(self)
        self._name_input.setPlaceholderText("Produto")

        # Quantity input — digits only
        self._quantity_input: QLineEdit = QLineEdit(self)
        self._quantity_input.setPlaceholderText("Qtde")
        self._quantity_input.setMaximumWidth(60)
        qty_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            r"^\d*$"
        )
        self._quantity_input.setValidator(qty_validator)

        # Price input — currency format
        self._price_input: QLineEdit = QLineEdit(self)
        self._price_input.setPlaceholderText("Preço un")
        price_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            r"^\d*([.,]\d{1,2})?$"
        )
        self._price_input.setValidator(price_validator)
        self._price_input.setMaximumWidth(100)

        # Price with freight input — read-only, gray, auto-calculated
        self._price_with_freight_input: QLineEdit = QLineEdit(self)
        self._price_with_freight_input.setPlaceholderText("Preço com frete")
        self._price_with_freight_input.setReadOnly(True)
        self._price_with_freight_input.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._price_with_freight_input.setStyleSheet("color: gray;")
        self._price_with_freight_input.setMaximumWidth(100)

        # Total input — read-only, gray
        self._total_with_freight_input: QLineEdit = QLineEdit(self)
        self._total_with_freight_input.setPlaceholderText("Preço total est")
        self._total_with_freight_input.setReadOnly(True)
        self._total_with_freight_input.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._total_with_freight_input.setStyleSheet("color: gray;")
        self._total_with_freight_input.setMaximumWidth(100)

        # Delete button
        self.delete_button: QPushButton = QPushButton("✕", self)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # Warning icon — shown when product has import warnings
        self.warning_icon: QLabel = QLabel(self)
        self.warning_icon.setFixedSize(18, 18)

        # Layout
        self._error: QLabel = QLabel("", self)

        # Error label styling: 9px, red
        _error_font: QFont = QFont()
        _error_font.setPixelSize(9)
        self._error.setFont(_error_font)
        self._error.setStyleSheet("color: #bc2f32;")
        self._error.setVisible(False)

        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 0)
        main_layout.setSpacing(0)

        row_layout: QHBoxLayout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self._name_input, stretch=1)
        row_layout.addWidget(self._quantity_input)
        row_layout.addWidget(self._price_input)
        row_layout.addWidget(self._price_with_freight_input)
        row_layout.addWidget(self._total_with_freight_input)
        row_layout.addWidget(self.warning_icon)
        row_layout.addWidget(self.delete_button)

        main_layout.addLayout(row_layout)
        main_layout.addWidget(self._error)

        # Signal connections for auto-calculation
        self._price_input.textChanged.connect(self._recalculate_total)
        self._quantity_input.textChanged.connect(self._recalculate_total)
        self._name_input.textChanged.connect(self._on_any_changed)
        self.delete_button.clicked.connect(self._on_delete)

        # Pre-fill if product_data provided
        if product_data is not None:
            self._name_input.setText(product_data.name)
            self._quantity_input.setText(str(product_data.quantity))
            self._price_input.setText(cents_to_input(getattr(product_data, "price", 0)))
            self._price_with_freight_input.setText(
                cents_to_input(getattr(product_data, "price_with_freight", product_data.price))
            )
            self._total_with_freight_input.setText(cents_to_input(getattr(product_data, "total", 0)))

        # Initial total calculation
        self._recalculate_total()

    def _recalculate_total(self) -> None:
        """Auto-calculate total from price × quantity."""
        if not self._name_input.text() and not self._price_input.text() and not self._quantity_input.text():
            return
        self._on_any_changed()
        price_cents: int = parse_currency_to_cents(self._price_with_freight_input.text())
        quantity_text: str = self._quantity_input.text().strip()
        quantity: int = int(quantity_text) if quantity_text else 0
        total_cents: int = price_cents * quantity
        self._total_with_freight_input.setText(cents_to_input(total_cents))


    def _on_any_changed(self) -> None:
        """Emit row_changed signal whenever any field changes."""
        self.row_changed.emit()

    def _on_delete(self) -> None:
        """Handle delete button click."""
        self.delete_pressed.emit()

    def set_price_with_freight(self, value_cents: int) -> None:
        """Set the read-only price_with_freight display value."""
        self._price_with_freight_input.setText(cents_to_input(value_cents))

    def set_total_with_freight(self, value_cents: int) -> None:
        self._total_with_freight_input.setText(cents_to_input(value_cents))

    def is_empty(self) -> bool:
        """Return True if name is empty AND quantity is 0 AND price is 0."""
        return (
                not self._name_input.text().strip()
                and not self._quantity_input.text().strip()
                and not self._price_input.text().strip()
        )

    def get_product_data(
            self, order_id: str, ordinal: int,
    ) -> ProductInput:
        """Return a ProductInput from the current widget state."""
        return ProductInput(
            id=self._id,
            name=self._name_input.text().strip(),
            quantity=self.get_quantity()
            if self._quantity_input.text().strip()
            else 0,
            price=self.get_price(),
            price_with_freight=self.get_price_with_freight(),
            total=self.get_total_price(),
            order_id=order_id,
            item_ordinal=ordinal,
        )

    def get_price(self) -> int:
        return parse_currency_to_cents(self._price_input.text())

    def get_price_with_freight(self):
        return parse_currency_to_cents(self._price_with_freight_input.text())

    def get_total_price_with_freight(self) -> int:
        return self.get_price_with_freight() * self.get_quantity()

    def get_total_price(self) -> int:
        return self.get_price() * self.get_quantity()

    def get_quantity(self) -> int:
        text = self._quantity_input.text().strip()
        if not text:
            return 0
        return int(text)

    def validate(self, *, show_errors: bool = False) -> tuple[bool, list[str]]:
        """
        Validate the row using requiredIfFilled logic.
        If any of name/quantity/price is filled, all three must be filled.
        Returns (True, []) if valid or fully empty; (False, [errors]) if partially filled.
        """
        name: str = self._name_input.text().strip()
        quantity_text: str = self._quantity_input.text().strip()
        price_text: str = self._price_input.text().strip()

        name_valid: bool = bool(name)
        quantity_valid: bool = bool(quantity_text) and int(quantity_text) > 0
        price_valid: bool = bool(price_text)

        filled_count: int = sum([name_valid, quantity_valid, price_valid])

        if 0 < filled_count < 3:
            errors: list[str] = []
            if not name_valid and (show_errors or self._name_input.isModified()):
                errors.append(
                    "Nome do produto obrigatório quando outros campos estão preenchidos."
                )
            if not quantity_valid and (show_errors or self._quantity_input.isModified()):
                errors.append(
                    "Quantidade do produto obrigatória quando outros campos estão preenchidos."
                )
            if not price_valid and (show_errors or self._price_input.isModified()):
                errors.append(
                    "Preço do produto obrigatório quando outros campos estão preenchidos."
                )
            if len(errors) > 0:
                self._error.setText(errors[0])
                self._error.setVisible(True)
            return False, errors

        self._error.setVisible(False)
        return True, []

    def set_warnings(self, warnings: list[str]) -> None:
        """Show warning icon with tooltip, or hide if no warnings."""
        if warnings:
            text = "; ".join(warnings)
            self.hover_filter = MouseHoverFilter(text, self.warning_icon)
            self.warning_icon.installEventFilter(self.hover_filter)
            self.warning_icon.setPixmap(svg_to_pixmap(_EXCLAMATION_ICON_PATH, 18, 18))


class MouseHoverFilter(QObject):
    def __init__(self, tooltip: str, parent: QWidget):
        super().__init__()
        self.custom_tip = MyCustomToolTip(tooltip)
        self.parent = parent

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            event: QMouseEvent = event  # type: ignore[union-attr]
            pos = self.parent.mapToGlobal(event.pos())
            self.custom_tip.move(pos)
            self.custom_tip.show()
            return True
        elif event.type() == QEvent.Type.Leave:
            if self.custom_tip:
                self.custom_tip.hide()
        return super().eventFilter(obj, event)


class MyCustomToolTip(QWidget):
    """An entirely custom widget acting as a tooltip popup."""

    def __init__(self, text, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Build your custom layout and design here
        layout = QVBoxLayout(self)
        self.label = QLabel(text, self)
        self.label.setStyleSheet("color: white; font-weight: bold;")
        self.setContentsMargins(0,0,0,0)
        layout.addWidget(self.label)

        self.setStyleSheet("""
            QWidget {
                background-color: #333333;
            }
        """)
