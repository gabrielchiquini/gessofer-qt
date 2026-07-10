from __future__ import annotations

from typing import Callable, List

from backend.injector_module import call_with_injection
from sqlalchemy.orm import Session

from backend.entities.orm import Expense
from backend.models.dto import ExpenseInput
from backend.repositories.expense_repository import ExpenseRepository
from backend.services.save_order_service import SaveExpenseService
from backend.utils.date import parse_month_for_expenses


def expenses_for_month(
    month: str,
    session_factory: Callable[[], Session],
) -> List[Expense]:
    """
    Fetch all expenses for a given month.

    Args:
        month: Month string in 'YYYY-MM' format (e.g., '2024-07').
        session_factory: Injected factory that creates new Sessions.

    Returns:
        List of Expense ORM entities.

    Raises:
        ValueError: If the month format is invalid.
        BackendError: If a database error occurs.
    """
    validated_month = parse_month_for_expenses(month)

    with session_factory() as session:
        repo = ExpenseRepository(session)
        return repo.fetch_expenses_for_month(month=validated_month)


def save_expenses(
    expenses: List[ExpenseInput],
    month: str,
    service: SaveExpenseService,
) -> None:
    """
    Save expenses in a single database transaction.

    This function is the API entry point for the 'save_expenses' command.
    It delegates all business logic to SaveExpenseService.

    Args:
        expenses: List of ExpenseInput DTOs to save.
        month: Month string in 'YYYY-MM' format.
        service: Injected SaveExpenseService instance.

    Raises:
        ValidationError: If input data fails validation.
        DatabaseError: If a database or transaction error occurs.
    """
    validated_month = parse_month_for_expenses(month)
    service.save_expenses(expenses=expenses, month=validated_month)


# Wrap functions with injection
def _expenses_for_month_injected(month: str) -> List[Expense]:
    """Injected wrapper for expenses_for_month."""
    return call_with_injection(expenses_for_month, month)


def _save_expenses_injected(
    expenses: List[ExpenseInput],
    month: str,
) -> None:
    """Injected wrapper for save_expenses."""
    call_with_injection(save_expenses, expenses, month)


def get_expenses_for_month_injected() -> Callable[[str], List[Expense]]:
    """Return the injected version of expenses_for_month for BackendManager."""
    return _expenses_for_month_injected


def get_save_expenses_injected() -> Callable[[List[ExpenseInput], str], None]:
    """Return the injected version of save_expenses for BackendManager."""
    return _save_expenses_injected
