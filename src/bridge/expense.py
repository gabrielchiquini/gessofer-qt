from __future__ import annotations

import logging

from backend.entities.orm import Expense
from backend.services.expense_fetch_handler import ExpenseFetchHandler
from backend.services.expense_save_handler import ExpenseSaveHandler
from models import ExpenseInput
from models.output import ExpenseOutput, ExpensesForMonthOutput

logger = logging.getLogger(__name__)


def expense_to_dict(expense: Expense) -> ExpenseOutput:
    """Transform an ORM Expense entity into a BridgeExpense dataclass."""
    return ExpenseOutput(
        id=expense.ID,
        month=expense.MONTH,
        description=expense.DESCRIPTION,
        value=expense.VALUE,
    )


class ExpenseBridge:
    """Bridge for expense-related fetch and save operations."""

    def __init__(
        self,
        expense_fetch_handler: ExpenseFetchHandler,
        expense_save_handler: ExpenseSaveHandler,
    ) -> None:
        self._expense_fetch_handler = expense_fetch_handler
        self._expense_save_handler = expense_save_handler

    def fetch_expenses_for_month(self, month: str) -> ExpensesForMonthOutput:
        """Fetch expenses for a given month."""
        try:
            m_str, y_str = month.strip().split("/")
            yyyy_mm = f"{y_str}-{m_str}"
            return self._expense_fetch_handler.fetch_expenses_for_month(yyyy_mm)
        except Exception as exc:
            logger.error("Error in fetch_expenses_for_month: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return ExpensesForMonthOutput(expenses=[], total=0)

    def save_expenses(
        self,
        expenses: list[ExpenseInput],
        month: str,
    ) -> bool:
        """Save a list of expenses for a given month."""
        try:
            m_str, y_str = month.strip().split("/")
            yyyy_mm = f"{y_str}-{m_str}"
            expense_inputs: list[ExpenseInput] = [
                ExpenseInput(description=e.description, value=e.value)
                for e in expenses
            ]
            self._expense_save_handler.save_expenses(expense_inputs, yyyy_mm)
            return True
        except Exception as exc:
            logger.error("Error in save_expenses: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return False

