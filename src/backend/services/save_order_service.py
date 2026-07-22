from __future__ import annotations

import logging
from typing import List

from injector import inject
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.errors import DatabaseError, ValidationError
from backend.models.dto import ExpenseInput, OrderInput
from backend.repositories.expense_repository import ExpenseRepository
from backend.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


class SaveOrderService:
    """
    Orchestrates the save-orders transaction.

    Algorithm (per Appendix B of business rules):
    1. Validate all input data.
    2. Begin a database transaction.
    3. Delete old orders (by ID) and their products.
    4. Insert new orders.
    5. Insert new products.
    6. Commit the transaction.

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

    def save_orders(
        self,
        orders: List[OrderInput],
        deleted_order_ids: List[str],
    ) -> None:
        """
        Save orders in a single transaction.

        Args:
            orders: List of OrderInput DTOs to insert.
            deleted_order_ids: List of order UUIDs to delete.

        Raises:
            ValidationError: If input data fails validation.
            DatabaseError: If a database error occurs.
        """
        # Step 1: Validate input
        validation_errors: list[str] = []
        for order in orders:
            if not order.id or not order.id.strip():
                validation_errors.append("ID de ordem vazio encontrado.")
            if not order.date or not order.date.strip():
                validation_errors.append(f"Data vazia na ordem {order.id}.")
            if not order.supplier or not order.supplier.strip():
                validation_errors.append(f"Fornecedor vazio na ordem {order.id}.")
            for product in order.products:
                if product.name and not product.quantity or product.quantity and not product.name:
                    validation_errors.append(
                        f"Nome e quantidade devem ser preenchidos juntos na ordem {order.id}."
                    )
                if product.price and (not product.quantity or not product.name):
                    validation_errors.append(
                        f"Preço requerido sem nome/quantidade na ordem {order.id}."
                    )

        if validation_errors:
            raise ValidationError(validation_errors, "Validação de pedidos falhou.")

        # Use injected engine to create session
        with Session(self._engine) as session:
            try:
                repo = OrderRepository(session)

                # Step 2: Delete old orders and their products
                if deleted_order_ids:
                    repo.delete_order_products(deleted_order_ids)
                    repo.delete_orders(deleted_order_ids)

                # Step 3: Insert new orders
                for order in orders:
                    repo.insert_order(order)

                # Step 4: Insert new products
                for order in orders:
                    for product in order.products:
                        repo.insert_product(product)

                # Session context manager commits on success, rolls back on exception
            except Exception as exc:
                logger.error("Erro ao salvar pedidos: %s", exc)
                raise DatabaseError(f"Falha na transação de salvamento de pedidos: {exc}") from exc

    def save_single_order(self, order: OrderInput) -> None:
        """
        Save a single order (with its products) as an upsert.

        If an order with the same ID already exists, its products and order row
        are deleted first, then the new data is inserted — all in one transaction.

        Args:
            order: Single OrderInput DTO to save.

        Raises:
            DatabaseError: If a database error occurs.
        """
        # Step 2: Upsert in a single transaction
        with Session(self._engine) as session:
            try:
                repo = OrderRepository(session)

                # Delete existing order + products (scoped to this single order)
                if order.id is not None:
                    repo.delete_order_products([order.id])
                    repo.delete_orders([order.id])

                # Insert the order
                repo.insert_order(order)

                # Insert the products
                for product in order.products:
                    repo.insert_product(product)

                session.commit()
            except Exception as exc:
                logger.error("Erro ao salvar pedido: %s", exc)
                raise DatabaseError(f"Falha na transação de salvamento de pedido: {exc}") from exc


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
        with Session(self._engine) as session:
            try:
                repo = ExpenseRepository(session)

                # Step 2: Delete existing expenses for the month
                repo.delete_expenses_for_month(month)

                # Step 3: Insert new expenses
                for expense in expenses:
                    repo.insert_expense(expense, month)

                # Session context manager commits on success, rolls back on exception
            except Exception as exc:
                logger.error("Erro ao salvar despesas: %s", exc)
                raise DatabaseError(f"Falha na transação de salvamento de despesas: {exc}") from exc
