from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.input import ExpenseInput
from backend.utils.currency import cents_to_input, parse_currency_to_cents
from models.output import ExpenseOutput


class ExpenseRowWidget(QWidget):
    """A single expense entry row with name and value fields and delete button."""

    row_changed: Signal = Signal()
    delete_pressed: Signal = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        expense_data: ExpenseOutput | None = None,
    ) -> None:
        super().__init__(parent)

        # Name input
        self.name_input: QLineEdit = QLineEdit(self)
        self.name_input.setPlaceholderText("Nome da despesa")

        # Value input — currency format
        self.value_input: QLineEdit = QLineEdit(self)
        self.value_input.setPlaceholderText("0,00")
        self.value_input.setMaximumWidth(120)
        value_validator: QRegularExpressionValidator = QRegularExpressionValidator(
            QRegularExpression(r"^\d*([.,]\d{1,2})?$")
        )
        self.value_input.setValidator(value_validator)

        # Delete button
        self.delete_button: QPushButton = QPushButton("✕", self)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # Error label
        self._error: QLabel = QLabel("", self)
        _error_font: QFont = QFont()
        _error_font.setPixelSize(9)
        self._error.setFont(_error_font)
        self._error.setStyleSheet("color: #bc2f32;")
        self._error.setVisible(False)

        # Layout
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 0)
        main_layout.setSpacing(0)

        row_layout: QHBoxLayout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self.name_input, stretch=1)
        row_layout.addWidget(self.value_input)
        row_layout.addWidget(self.delete_button)

        main_layout.addLayout(row_layout)
        main_layout.addWidget(self._error)

        # Signal connections
        self.name_input.textChanged.connect(self._on_any_changed)
        self.value_input.textChanged.connect(self._on_any_changed)
        self.delete_button.clicked.connect(self._on_delete)

        # Pre-fill if expense_data provided
        if expense_data is not None:
            self.name_input.setText(expense_data.description)
            self.value_input.setText(cents_to_input(expense_data.value))

    def _on_any_changed(self) -> None:
        """Emit row_changed signal whenever any field changes."""
        self.row_changed.emit()

    def _on_delete(self) -> None:
        """Handle delete button click."""
        self.delete_pressed.emit()

    def is_empty(self) -> bool:
        """Return True if both name and value inputs are empty/whitespace."""
        return (
            not self.name_input.text().strip()
            and not self.value_input.text().strip()
        )

    def get_expense_data(self) -> ExpenseInput:
        """Return an ExpenseInput from the current widget state."""
        name: str = self.name_input.text().strip()
        value_text: str = self.value_input.text().strip()
        if not name and not value_text:
            return ExpenseInput(description="", value=0)
        return ExpenseInput(
            description=name,
            value=parse_currency_to_cents(value_text),
        )

    def validate(self, *, show_errors: bool = False) -> tuple[bool, list[str]]:
        """
        Validate the row using requiredIfFilled logic.
        If exactly one of name/value is filled, it's an error.
        Both empty → valid (row will be discarded).
        Both filled → valid.
        Returns (True, []) if valid, (False, [errors]) if invalid.
        """
        name: str = self.name_input.text().strip()
        value_text: str = self.value_input.text().strip()
        name_filled: bool = bool(name)
        value_filled: bool = bool(value_text)

        # Both empty → valid (row will be discarded)
        if not name_filled and not value_filled:
            self._error.setVisible(False)
            return True, []

        # One filled, other empty → error
        if name_filled != value_filled:
            errors: list[str] = []
            if not name_filled and (show_errors or self.name_input.isModified()):
                errors.append("Descrição obrigatória quando o valor está preenchido.")
            if not value_filled and (show_errors or self.value_input.isModified()):
                errors.append("Valor obrigatório quando a descrição está preenchida.")
            if errors:
                self._error.setText(errors[0])
                self._error.setVisible(True)
            return False, errors

        # Both filled → valid
        self._error.setVisible(False)
        return True, []
