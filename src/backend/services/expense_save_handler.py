from __future__ import annotations

import logging

from injector import inject

from models.input import ExpenseInput
from backend.services.save_order_service import SaveExpenseService

logger = logging.getLogger(__name__)


class ExpenseSaveHandler:
    """Save handler for expenses."""

    @inject
    def __init__(self, save_expense_service: SaveExpenseService) -> None:
        self._save_expense_service = save_expense_service

    def save_expenses(
        self,
        expenses: list[ExpenseInput],
        month: str,
    ) -> None:
        """Save expenses in a single transaction."""
        self._save_expense_service.save_expenses(expenses, month)
