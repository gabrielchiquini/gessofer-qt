from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtWidgets import QWidget

from bridge.expense import ExpenseBridge
from frontend.views.expense_edit.expense_edit_dialog import ExpenseEditDialog


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class ExpenseEditDialogFactory(Protocol):
    """Factory protocol for creating ExpenseEditDialog instances."""

    def __call__(self, parent: QWidget, month: str) -> ExpenseEditDialog: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _ExpenseEditDialogFactoryImpl:
    """Implementation of ExpenseEditDialogFactory backed by a DI-resolved ExpenseBridge."""

    def __init__(self, expense_bridge: ExpenseBridge) -> None:
        self._expense_bridge: ExpenseBridge = expense_bridge

    def __call__(self, parent: QWidget, month: str) -> ExpenseEditDialog:
        return ExpenseEditDialog(
            parent=parent,
            month=month,
            expense_bridge=self._expense_bridge,
        )


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helper
# ──────────────────────────────────────────────────────────────────────


def _make_expense_edit_dialog_factory(injector: Any) -> ExpenseEditDialogFactory:
    """Create a closure-based ExpenseEditDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    expense_bridge = inv.get(ExpenseBridge)
    return _ExpenseEditDialogFactoryImpl(expense_bridge=expense_bridge)
