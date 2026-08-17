from __future__ import annotations

import logging

from backend.entities.orm import Expense
from backend.injector_module import get_injector
from models import ExpenseInput
from backend.services.expense_fetch_handler import ExpenseFetchHandler
from backend.services.expense_save_handler import ExpenseSaveHandler
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


def fetch_expenses_for_month(month: str) -> ExpensesForMonthOutput:
    """
    Fetch expenses for a given month.

    Args:
        month: Month in MM/yyyy format (will be converted to YYYY-MM).

    Returns:
        ExpensesForMonthOutput with the list of expenses and the total value.
        On error, returns an ExpensesForMonthOutput with empty expenses and total 0.
    """
    try:
        handler = get_injector().get(ExpenseFetchHandler)
        # Convert MM/yyyy to YYYY-MM
        m_str, y_str = month.strip().split("/")
        yyyy_mm = f"{y_str}-{m_str}"
        return handler.fetch_expenses_for_month(yyyy_mm)
    except Exception as exc:
        logger.error("Error in fetch_expenses_for_month: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return ExpensesForMonthOutput(expenses=[], total=0)


def save_expenses(
    expenses: list[ExpenseInput],
    month: str,
) -> bool:
    """
    Save a list of expenses for a given month.

    Args:
        expenses: List of ExpenseInput dataclass instances.
        month: Month in MM/yyyy format (will be converted to YYYY-MM).

    Returns:
        True on success, False on error.
    """
    try:
        handler = get_injector().get(ExpenseSaveHandler)
        m_str, y_str = month.strip().split("/")
        yyyy_mm = f"{y_str}-{m_str}"
        expense_inputs: list[ExpenseInput] = [
            ExpenseInput(description=e.description, value=e.value)
            for e in expenses
        ]
        handler.save_expenses(expense_inputs, yyyy_mm)
        return True
    except Exception as exc:
        logger.error("Error in save_expenses: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return False
