from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from models.input import ExpenseInput
from backend.utils.currency import cents_to_view, parse_currency_to_cents
from models.output import ExpenseOutput
from frontend.components.card import Card
from frontend.views.expense_edit.expense_row_widget import ExpenseRowWidget


class ExpenseItemsCard(QWidget):
    """Container for a list of ExpenseRowWidget instances with total footer."""

    expense_changed: Signal = Signal()

    def __init__(self, parent: QWidget, month: str) -> None:
        super().__init__(parent)

        # ── Card Container ────────────────────────────────────────────
        self._card: Card = Card(self)
        self._card.set_title(f"Despesas de {month}")

        # ── Expense Rows Container ────────────────────────────────────
        self.expenses_layout: QVBoxLayout = QVBoxLayout()
        self.expenses_layout.setSpacing(0)
        self.expenses_layout.setContentsMargins(0, 0, 0, 0)
        self.expenses_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._expense_rows: list[ExpenseRowWidget] = []

        # ── Scroll Area for Expense Rows ────────────────────────────────
        self._scroll_container: QWidget = QWidget()
        self._scroll_container.setContentsMargins(0, 0, 0, 0)
        self._scroll_container.setObjectName("scroll_container")
        self._scroll_container.setStyleSheet(
            "#scroll_container { background-color: white; border: 0px; border-radius: 0px; }")
        self._scroll_container.setLayout(self.expenses_layout)

        self._scroll_area: QScrollArea = QScrollArea(self)
        self._scroll_area.setWidget(self._scroll_container)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._card.set_content(self._scroll_area)

        # ── Footer ────────────────────────────────────────────────────
        self.total_label: QLabel = QLabel(
            "Total: R$ 0,00", self
        )

        footer_layout: QHBoxLayout = QHBoxLayout()
        footer_layout.addWidget(self.total_label)
        footer_layout.addStretch()

        self._card.build_footer()
        self._card.set_footer(footer_layout)

        # ── Main Layout ───────────────────────────────────────────────
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(self._card)

    # ── Row Management ──────────────────────────────────────────────

    def _add_empty_row(self) -> ExpenseRowWidget:
        """Add a new empty expense row to the layout."""
        row = self.setup_row()
        self._update_delete_buttons()
        return row

    def _on_row_changed(self) -> None:
        """Handle changes in an expense row: auto-add if last row filled."""
        changed_row: ExpenseRowWidget = self.sender()  # type: ignore[union-attr]
        changed_row.validate()
        last_row = self._expense_rows[-1]
        if not last_row.is_empty() and changed_row is last_row:
            self._add_empty_row()
        self._expense_changed()

    def _update_delete_buttons(self) -> None:
        """Enable delete button only for non-last rows."""
        for i, row in enumerate(self._expense_rows):
            row.delete_button.setEnabled(i < len(self._expense_rows) - 1)

    # ── Data Access ─────────────────────────────────────────────────

    def get_expenses_list(self) -> list[ExpenseInput]:
        """Return list of ExpenseInput from all rows except the trailing empty row."""
        return [
            row.get_expense_data() for row in self._expense_rows[:-1]
        ]

    def validate(self, *, show_errors: bool = False) -> tuple[bool, list[str]]:
        """
        Validate each expense row.
        Returns (True, []) if all valid, (False, [errors]) with prefixed errors if any invalid.
        """
        errors: list[str] = []
        for i, row in enumerate(self._expense_rows):
            valid, row_errors = row.validate(show_errors=show_errors)
            if not valid:
                for err in row_errors:
                    errors.append(f"Despesa {i + 1}: {err}")
        return len(errors) == 0, errors

    def get_expense_rows(self) -> list[ExpenseRowWidget]:
        """Return the _expense_rows list for external access."""
        return self._expense_rows

    # ── Data Loading ────────────────────────────────────────────────

    def set_expenses_data(self, expenses: list[ExpenseOutput]) -> None:
        """Replace all rows with data from expenses list."""
        for row in self._expense_rows:
            self.expenses_layout.removeWidget(row)
            row.deleteLater()
        self._expense_rows.clear()

        for expense in expenses:
            self.setup_row(expense_data=expense)
        self._add_empty_row()
        self._update_delete_buttons()
        self._expense_changed()

    def setup_row(self, *, expense_data: ExpenseOutput | None = None) -> ExpenseRowWidget:
        """Create a row, append to list and layout, connect signals, return row."""
        row = ExpenseRowWidget(self, expense_data=expense_data)
        self._expense_rows.append(row)
        self.expenses_layout.addWidget(row)
        row.row_changed.connect(self._on_row_changed)
        row.delete_pressed.connect(self.delete_row)
        return row

    def add_row(self, expense_data: ExpenseOutput | None = None) -> ExpenseRowWidget:
        """Public method to add a row with optional pre-filled data."""
        row = self.setup_row(expense_data=expense_data)
        self._update_delete_buttons()
        return row

    def delete_row(self) -> None:
        """Remove the sender row from layout, delete widget, pop from list."""
        row: ExpenseRowWidget = self.sender()  # type: ignore[union-attr]
        if row is None:
            raise RuntimeError("delete_row must be called via signal or with explicit row parameter")
        row.deleteLater()
        self.expenses_layout.removeWidget(row)
        index = self._expense_rows.index(row)
        self._expense_rows.pop(index)
        self._update_delete_buttons()
        self._expense_changed()

    def _expense_changed(self) -> None:
        """Update total label and emit expense_changed signal."""
        total_cents: int = sum(
            parse_currency_to_cents(row.value_input.text())
            for row in self._expense_rows[:-1]  # skip trailing empty row
        )
        self.total_label.setText(f"Total: {cents_to_view(total_cents)}")
        self.expense_changed.emit()
