from __future__ import annotations

import logging
from typing import Callable

from injector import inject
from sqlalchemy.orm import Session

from backend.entities.orm import Expense
from backend.repositories.expense_repository import ExpenseRepository
from bridge.models.expense import ExpenseOutput, ExpensesForMonthOutput

logger = logging.getLogger(__name__)


class ExpenseFetchHandler:
    """Fetch handler for expenses."""

    @inject
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def fetch_expenses_for_month(
        self,
        month: str,
    ) -> ExpensesForMonthOutput:
        """Fetch expenses for a month in YYYY-MM format."""
        session: Session = self._session_factory()
        try:
            repo = ExpenseRepository(session)
            expenses = repo.fetch_expenses_for_month(month)
            outputs: list[ExpenseOutput] = [_expense_to_dict(e) for e in expenses]
            total: int = sum(o.value for o in outputs)
            return ExpensesForMonthOutput(expenses=outputs, total=total)
        except Exception as exc:
            logger.error("Error fetching expenses: %s", exc)
            raise
        finally:
            session.close()


def _expense_to_dict(expense: Expense) -> ExpenseOutput:
    """Transform an ORM Expense entity into a BridgeExpense dataclass."""
    return ExpenseOutput(
        id=expense.ID,
        month=expense.MONTH,
        description=expense.DESCRIPTION,
        value=expense.VALUE,
    )
