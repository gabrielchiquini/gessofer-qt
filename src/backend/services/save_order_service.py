from __future__ import annotations

import logging
from typing import List

from injector import inject
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.errors import DatabaseError, ValidationError
from backend.repositories.order_repository import OrderRepository
from models.input import OrderInput

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
