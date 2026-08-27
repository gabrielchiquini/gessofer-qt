from __future__ import annotations

import logging
from typing import Callable

from injector import inject
from sqlalchemy.orm import Session

from backend.entities.orm import ExpenseEntity
from backend.repositories.expense_repository import ExpenseRepository
from backend.services.save_expense_service import SaveExpenseService
from models.input import ExpenseInput
from models.output import ExpenseOutput, ExpensesForMonthOutput

logger = logging.getLogger(__name__)


def _expense_to_dict(expense: ExpenseEntity) -> ExpenseOutput:
    """Transform an ORM Expense entity into an ExpenseOutput dataclass."""
    return ExpenseOutput(
        id=expense.ID,
        month=expense.MONTH,
        description=expense.DESCRIPTION,
        value=expense.VALUE,
    )


class ExpenseService:
    """Unified service for expense fetch and save operations.

    Merges the responsibilities of the former ExpenseBridge,
    ExpenseFetchHandler, and ExpenseSaveHandler into a single class.

    - fetch_expenses_for_month: session-per-call fetch with error handling.
    - save_expenses: delegates to SaveExpenseService with error handling.
    - Month format: accepts "MM/yyyy" (display format), converts to "YYYY-MM" internally.
    """

    @inject
    def __init__(
        self,
        save_expense_service: SaveExpenseService,
        session_factory: Callable[[], Session],
    ) -> None:
        self._save_expense_service = save_expense_service
        self._session_factory = session_factory

    def fetch_expenses_for_month(self, month: str) -> ExpensesForMonthOutput:
        """Fetch expenses for a given month in MM/yyyy display format."""
        try:
            m_str, y_str = month.strip().split("/")
            yyyy_mm = f"{y_str}-{m_str}"
            session: Session = self._session_factory()
            try:
                repo = ExpenseRepository(session)
                expenses = repo.fetch_expenses_for_month(yyyy_mm)
                outputs: list[ExpenseOutput] = [_expense_to_dict(e) for e in expenses]
                total: int = sum(o.value for o in outputs)
                return ExpensesForMonthOutput(expenses=outputs, total=total)
            finally:
                session.close()
        except Exception as exc:
            logger.error("Error in fetch_expenses_for_month: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return ExpensesForMonthOutput(expenses=[], total=0)

    def save_expenses(
        self,
        expenses: list[ExpenseInput],
        month: str,
    ) -> bool:
        """Save a list of expenses for a given month in MM/yyyy display format."""
        try:
            m_str, y_str = month.strip().split("/")
            yyyy_mm = f"{y_str}-{m_str}"
            expense_inputs: list[ExpenseInput] = [
                ExpenseInput(description=e.description, value=e.value)
                for e in expenses
            ]
            self._save_expense_service.save_expenses(expense_inputs, yyyy_mm)
            return True
        except Exception as exc:
            logger.error("Error in save_expenses: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return False
