from __future__ import annotations

import uuid
from pathlib import Path

from Custom_Widgets.QCustomQToolTip import QCustomQToolTip
from PySide6.QtCore import Signal, Qt, QObject, QEvent
from PySide6.QtGui import QRegularExpressionValidator, QFont, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget, QToolTip,
)

from backend import ProductInput
from backend.utils.currency import cents_to_display, parse_currency_to_cents
from bridge.models.product import Product
from frontend.util.icons import svg_to_pixmap

_EXCLAMATION_ICON_PATH = str(Path(__file__).parent.parent.parent / "assets" / "circle-exclamation.svg")
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
        self.name_input: QLineEdit = QLineEdit(self)
        self.name_input.setPlaceholderText("Produto")

        # Quantity input — digits only
        self.quantity_input: QLineEdit = QLineEdit(self)
        self.quantity_input.setPlaceholderText("Qtde")
        self.quantity_input.setMaximumWidth(60)
        qty_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            r"^\d*$"
        )
        self.quantity_input.setValidator(qty_validator)

        # Price input — currency format
        self.price_input: QLineEdit = QLineEdit(self)
        self.price_input.setPlaceholderText("0,00")
        price_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            r"^\d*([.,]\d{1,2})?$"
        )
        self.price_input.setValidator(price_validator)
        self.price_input.setMaximumWidth(120)

        # Total input — read-only, gray
        self.total_input: QLineEdit = QLineEdit(self)
        self.total_input.setPlaceholderText("0,00")
        self.total_input.setReadOnly(True)
        self.total_input.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.total_input.setStyleSheet("color: gray;")
        self.total_input.setMaximumWidth(120)

        # Delete button
        self.delete_button: QPushButton = QPushButton("✕", self)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # Warning icon — shown when product has import warnings
        assets_dir: Path = Path(__file__).parent.parent / "assets"
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
        row_layout.addWidget(self.name_input, stretch=1)
        row_layout.addWidget(self.quantity_input)
        row_layout.addWidget(self.price_input)
        row_layout.addWidget(self.total_input)
        row_layout.addWidget(self.warning_icon)
        row_layout.addWidget(self.delete_button)

        main_layout.addLayout(row_layout)
        main_layout.addWidget(self._error)

        # Signal connections for auto-calculation
        self.price_input.textChanged.connect(self._recalculate_total)
        self.quantity_input.textChanged.connect(self._recalculate_total)
        self.name_input.textChanged.connect(self._on_any_changed)
        self.delete_button.clicked.connect(self._on_delete)

        # Pre-fill if product_data provided
        if product_data is not None:
            self.name_input.setText(product_data.name)
            self.quantity_input.setText(str(product_data.quantity))
            self.price_input.setText(cents_to_display(getattr(product_data, "price", 0)))
            self.total_input.setText(cents_to_display(getattr(product_data, "total", 0)))

        # Initial total calculation
        self._recalculate_total()

    def _recalculate_total(self) -> None:
        """Auto-calculate total from price × quantity."""
        price_cents: int = parse_currency_to_cents(self.price_input.text())
        quantity_text: str = self.quantity_input.text().strip()
        quantity: int = int(quantity_text) if quantity_text else 0
        total_cents: int = price_cents * quantity
        self.total_input.setText(cents_to_display(total_cents))
        self._on_any_changed()

    def _on_any_changed(self) -> None:
        """Emit row_changed signal whenever any field changes."""
        self.row_changed.emit()

    def _on_delete(self) -> None:
        """Handle delete button click."""
        self.delete_pressed.emit()

    def is_empty(self) -> bool:
        """Return True if name is empty AND quantity is 0 AND price is 0."""
        return (
                not self.name_input.text().strip()
                and not self.quantity_input.text().strip()
                and not self.price_input.text().strip()
        )

    def get_product_data(
            self, order_id: str, ordinal: int,
    ) -> ProductInput:
        """Return a ProductInput from the current widget state."""
        return ProductInput(
            id=self._id,
            name=self.name_input.text().strip(),
            quantity=int(self.quantity_input.text())
            if self.quantity_input.text().strip()
            else 0,
            price=parse_currency_to_cents(self.price_input.text()),
            total=parse_currency_to_cents(self.total_input.text()),
            order_id=order_id,
            item_ordinal=ordinal,
        )

    def validate(self, *, show_errors: bool = False) -> tuple[bool, list[str]]:
        """
        Validate the row using requiredIfFilled logic.
        If any of name/quantity/price is filled, all three must be filled.
        Returns (True, []) if valid or fully empty; (False, [errors]) if partially filled.
        """
        name: str = self.name_input.text().strip()
        quantity_text: str = self.quantity_input.text().strip()
        price_text: str = self.price_input.text().strip()

        name_valid: bool = bool(name)
        quantity_valid: bool = bool(quantity_text)
        price_valid: bool = bool(price_text)

        filled_count: int = sum([name_valid, quantity_valid, price_valid])

        if 0 < filled_count < 3:
            errors: list[str] = []
            if not name_valid and (show_errors or self.name_input.isModified()):
                errors.append(
                    "Nome do produto obrigatório quando outros campos estão preenchidos."
                )
            if not quantity_valid and (show_errors or self.quantity_input.isModified()):
                errors.append(
                    "Quantidade do produto obrigatória quando outros campos estão preenchidos."
                )
            if not price_valid and (show_errors or self.price_input.isModified()):
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
            # self.hover_filter = MouseHoverFilter(text)
            # self.warning_icon.installEventFilter(self.hover_filter)
            self.warning_icon.setPixmap(svg_to_pixmap(_EXCLAMATION_ICON_PATH, 18, 18))
            QCustomQToolTip(
                text=text,
                parent=self,
                target=self.warning_icon,
                duration=1500,
                tailPosition="top-center"
            )
            self.warning_icon.setToolTip(text)
        else:
            self.warning_icon.setToolTip("")

class MouseHoverFilter(QObject):
    def __init__(self, tooltip: str):
        super().__init__()
        self.tooltip = tooltip


    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            event: QMouseEvent = event # type: ignore[union-attr]
            QToolTip.showText(event.globalPos(), self.tooltip)
        elif event.type() == QEvent.Type.Leave:
            event: QMouseEvent = event # type: ignore[union-attr]

        return super().eventFilter(obj, event)
