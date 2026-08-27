from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy.orm import Session

from backend.entities.adapter import orm_order_to_model
from backend.repositories.order_repository import OrderRepository
from backend.services.order_service import OrderService
from models.input import OrderInput
from models.order import Order

logger = logging.getLogger(__name__)


class OrderBridge:
    """Bridge for order-related save and fetch operations."""

    def __init__(
            self,
            order_service: OrderService,
            session_factory: Callable[[], Session],
    ) -> None:
        self._order_service = order_service
        self._session_factory = session_factory

    def save_single_order(self, order: OrderInput) -> bool:
        """Save a single order (with its products) as an upsert."""
        try:
            self._order_service.save_single_order(order)
            return True
        except Exception as exc:
            logger.error("Error in save_single_order: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return False

    def fetch_order_by_id(self, order_id: str) -> Order | None:
        """Fetch a single order by UUID, including all products."""
        session: Session = self._session_factory()
        try:
            repo = OrderRepository(session)
            order = repo.fetch_order_by_id(order_id)
            if order is None:
                return None
            return orm_order_to_model(order)
        finally:
            session.close()

    def delete_order(self, order_id: str) -> bool:
        """Delete an order and its associated products."""
        try:
            session: Session = self._session_factory()
            try:
                repo = OrderRepository(session)
                repo.delete_order_products([order_id])
                repo.delete_orders([order_id])
                session.commit()
                return True
            finally:
                session.close()
        except Exception as exc:
            logger.error("Error in delete_order: %s", exc)
            return False
