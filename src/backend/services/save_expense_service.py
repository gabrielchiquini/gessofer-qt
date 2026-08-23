from __future__ import annotations

from typing import List

from injector import inject
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.errors import ValidationError, DatabaseError
from backend.repositories.expense_repository import ExpenseRepository
from backend.services.save_order_service import logger
from models.input import ExpenseInput


class SaveExpenseService:
    """
    Orchestrates the save-expenses transaction.

    Algorithm (per Appendix B of business rules):
    1. Validate all input data.
    2. Begin a database transaction.
    3. Delete existing expenses for the month.
    4. Insert new expenses.
    5. Commit the transaction.

    If any step fails, rollback is automatic.
    """

    @inject
    def __init__(self, engine: Engine) -> None:
        """
        Initialize with an injected Engine.

        Args:
            engine: The shared SQLAlchemy Engine (injected by the DI container).
        """
        self._engine = engine

    def save_expenses(
        self,
        expenses: List[ExpenseInput],
        month: str,
    ) -> None:
        """
        Save expenses in a single transaction.

        Args:
            expenses: List of ExpenseInput DTOs to insert.
            month: Month string in 'YYYY-MM' format.

        Raises:
            ValidationError: If input data fails validation.
            DatabaseError: If a database error occurs.
        """
        # Step 1: Validate input
        validation_errors: list[str] = []
        for expense in expenses:
            has_desc = bool(expense.description and expense.description.strip())
            has_value = expense.value is not None and expense.value != 0
            if has_desc != has_value:
                # One is filled but not the other — both or neither
                if has_desc:
                    validation_errors.append(
                        "Valor de despesa obrigatório quando descrição está preenchida."
                    )
                else:
                    validation_errors.append(
                        "Descrição de despesa obrigatória quando valor está preenchido."
                    )

        if validation_errors:
            raise ValidationError(validation_errors, "Validação de despesas falhou.")

        # Use injected engine to create session
        with Session(self._engine).begin() as transaction:
            try:
                repo = ExpenseRepository(transaction)


                # Step 2: Delete existing expenses for the month
                repo.delete_expenses_for_month(month)

                # Step 3: Insert new expenses
                for expense in expenses:
                    repo.insert_expense(expense, month)
                transaction.commit()

            except Exception as exc:
                logger.error("Erro ao salvar despesas: %s", exc)
                raise DatabaseError(f"Falha na transação de salvamento de despesas: {exc}") from exc
