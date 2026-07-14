from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy.orm import Session

from bridge import ExpenseDict, ExpenseInputDict
from backend.database.connection import get_engine
from backend.injector_module import get_injector
from backend.models.dto import ExpenseInput
from backend.utils.transformers import expense_to_dict
from backend.repositories.expense_repository import ExpenseRepository
from backend.repositories.order_repository import OrderRepository
from backend.services.save_order_service import SaveExpenseService, SaveOrderService
from backend.utils.date import parse_month_for_expenses

logger = logging.getLogger(__name__)


class _ExpenseFetchHandler:
    """Fetch handler for expenses."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def fetch_expenses_for_month(self, month: str) -> list[ExpenseDict]:
        """Fetch expenses for a month in YYYY-MM format."""
        session: Session = self._session_factory()
        try:
            repo = ExpenseRepository(session)
            expenses = repo.fetch_expenses_for_month(month)
            return [expense_to_dict(e) for e in expenses]
        except Exception as exc:
            logger.error("Error fetching expenses: %s", exc)
            raise
        finally:
            session.close()


class _ExpenseSaveHandler:
    """Save handler for expenses."""

    def __init__(self, save_expense_service: SaveExpenseService) -> None:
        self._save_expense_service = save_expense_service

    def save_expenses(
        self,
        expenses: list[ExpenseInput],
        month: str,
    ) -> None:
        """Save expenses in a single transaction."""
        self._save_expense_service.save_expenses(expenses, month)


_fetch_handler: _ExpenseFetchHandler | None = None
_save_handler: _ExpenseSaveHandler | None = None
_session_factory: Callable[[], Session] | None = None


def _get_fetch_handler() -> _ExpenseFetchHandler:
    """Lazy-initialize the expense fetch handler."""
    global _fetch_handler, _session_factory
    if _fetch_handler is None:
        engine = get_engine()

        def _session_factory() -> Session:
            from sqlalchemy.orm import Session as SA_Session
            return SA_Session(engine)

        _session_factory = _session_factory
        _fetch_handler = _ExpenseFetchHandler(_session_factory)
    return _fetch_handler


def _get_save_handler() -> _ExpenseSaveHandler:
    """Lazy-initialize the expense save handler."""
    global _save_handler
    if _save_handler is None:
        injector = get_injector()
        save_expense_service = injector.get(SaveExpenseService)
        _save_handler = _ExpenseSaveHandler(save_expense_service)
    return _save_handler


def fetch_expenses_for_month(month: str) -> list[ExpenseDict]:
    """
    Fetch expenses for a given month.

    Args:
        month: Month in MM/yyyy format (will be converted to YYYY-MM).

    Returns:
        List of expense dicts. On error, returns [].
    """
    try:
        handler = _get_fetch_handler()
        # Convert MM/yyyy to YYYY-MM
        m_str, y_str = month.strip().split("/")
        yyyy_mm = f"{y_str}-{m_str}"
        return handler.fetch_expenses_for_month(yyyy_mm)
    except Exception as exc:
        logger.error("Error in fetch_expenses_for_month: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return []


def save_expenses(
    expenses: list[ExpenseInputDict],
    month: str,
) -> bool:
    """
    Save a list of expenses for a given month.

    Args:
        expenses: List of expense dicts with 'description' and 'value' keys.
        month: Month in MM/yyyy format (will be converted to YYYY-MM).

    Returns:
        True on success, False on error.
    """
    try:
        handler = _get_save_handler()
        m_str, y_str = month.strip().split("/")
        yyyy_mm = f"{y_str}-{m_str}"
        expense_inputs: list[ExpenseInput] = [
            ExpenseInput(description=e["description"], value=e["value"])
            for e in expenses
        ]
        handler.save_expenses(expense_inputs, yyyy_mm)
        return True
    except Exception as exc:
        logger.error("Error in save_expenses: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return False
