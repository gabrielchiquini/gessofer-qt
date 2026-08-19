from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from PySide6.QtWidgets import QWidget

from bridge.expense import ExpenseBridge
from frontend.views.expense_list import ExpenseListView
from frontend.factories.expense_edit_dialog_factory import ExpenseEditDialogFactory


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class ExpenseListViewFactory(Protocol):
    """Factory protocol for creating ExpenseListView instances."""

    def __call__(self, parent: QWidget) -> ExpenseListView: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _ExpenseListViewFactoryImpl:
    """Implementation of ExpenseListViewFactory backed by DI-resolved dependencies."""

    def __init__(
        self,
        expense_bridge: ExpenseBridge,
        expense_edit_dialog_factory: ExpenseEditDialogFactory,
    ) -> None:
        self._expense_bridge: ExpenseBridge = expense_bridge
        self._expense_edit_dialog_factory: ExpenseEditDialogFactory = expense_edit_dialog_factory

    def __call__(self, parent: QWidget) -> ExpenseListView:
        return ExpenseListView(
            parent=parent,
            expense_bridge=self._expense_bridge,
            expense_edit_dialog_factory=self._expense_edit_dialog_factory,
        )
