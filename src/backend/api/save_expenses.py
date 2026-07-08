from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.entities.orm import Expense
from backend.models.dto import ExpenseInput
from backend.repositories.expense_repository import ExpenseRepository
from backend.services.save_order_service import SaveExpenseService
from backend.utils.date import parse_month_for_expenses


def expenses_for_month(month: str) -> List[Expense]:
    """
    Fetch all expenses for a given month.

    Args:
        month: Month string in 'YYYY-MM' format (e.g., '2024-07').

    Returns:
        List of Expense ORM entities.

    Raises:
        ValueError: If the month format is invalid.
        BackendError: If a database error occurs.
    """
    validated_month = parse_month_for_expenses(month)

    engine = get_engine()
    with Session(engine) as session:
        repo = ExpenseRepository(session)
        return repo.fetch_expenses_for_month(month=validated_month)


def save_expenses(
    expenses: List[ExpenseInput],
    month: str,
) -> None:
    """
    Save expenses in a single database transaction.

    This function is the API entry point for the 'save_expenses' command.
    It delegates all business logic to SaveExpenseService.

    Args:
        expenses: List of ExpenseInput DTOs to save.
        month: Month string in 'YYYY-MM' format.

    Raises:
        ValidationError: If input data fails validation.
        BackendError: If a database or transaction error occurs.
    """
    validated_month = parse_month_for_expenses(month)

    service = SaveExpenseService()
    service.save_expenses(expenses=expenses, month=validated_month)
