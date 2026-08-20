from __future__ import annotations

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.input import ExpenseInput
from bridge.expense import ExpenseBridge
from frontend.views.expense_edit.expense_items_card import ExpenseItemsCard


class ExpenseEditDialog(QDialog):
    """Modal dialog for editing expenses of a given month."""

    expenses_saved: Signal = Signal(str)
    closed: Signal = Signal()

    def __init__(
            self,
            parent: QWidget | None,
            month: str,
            expense_bridge: ExpenseBridge,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumSize(800, 600)

        # Use current month if none provided
        self._month: str = month

        # ── DI Bridge ─────────────────────────────────────────────────
        self._expense_bridge: ExpenseBridge = expense_bridge

        # ── Items Card ────────────────────────────────────────────────
        self.items_card: ExpenseItemsCard = ExpenseItemsCard(self, month)

        # Load existing expenses
        expenses_data = self._expense_bridge.fetch_expenses_for_month(self._month)
        self.items_card.set_expenses_data(expenses_data.expenses)

        # ── Footer Buttons ────────────────────────────────────────────
        self.btn_save: QPushButton = QPushButton("Salvar", self)
        self.btn_save.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.btn_close: QPushButton = QPushButton("Fechar", self)
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # ── Main Layout ───────────────────────────────────────────────
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        # Items card (stretch = 1, takes remaining space)
        layout.addWidget(self.items_card, 1)

        # Message label
        self.message_label: QLabel = QLabel(self)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        # Footer frame
        footer_frame: QHBoxLayout = QHBoxLayout()
        footer_frame.addWidget(self.btn_save)
        footer_frame.addStretch()
        footer_frame.addWidget(self.btn_close)

        footer_container = QWidget(self)
        footer_container.setLayout(footer_frame)
        layout.addWidget(footer_container)

        # ── Signal Connections ────────────────────────────────────────
        self.btn_save.clicked.connect(self._on_save)
        self.btn_close.clicked.connect(self._on_close)

    def _on_save(self) -> None:
        """Handle save button click."""
        valid, errors = self.items_card.validate(show_errors=True)
        if not valid:
            return

        expenses_list: list[ExpenseInput] = self.items_card.get_expenses_list()
        success: bool = self._expense_bridge.save_expenses(expenses_list, self._month)
        if success:
            self._show_message("Salvo com sucesso!", "success")
            self.expenses_saved.emit(self._month)
            self.accept()
        else:
            self._show_message("Erro ao salvar despesa.", "error")

    def _on_close(self) -> None:
        """Handle close button click."""
        self.reject()
        self.closed.emit()

    def _show_message(self, text: str, level: str) -> None:
        """Show a styled message in the message label, auto-clear after 5 seconds."""
        colors: dict[str, str] = {
            "success": "background-color: #d4edda; color: #155724;",
            "error": "background-color: #f8d7da; color: #721c24;",
        }
        self.message_label.setText(text)
        self.message_label.setStyleSheet(colors.get(level, ""))
        QTimer.singleShot(5000, self.message_label.clear)
