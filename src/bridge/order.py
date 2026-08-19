from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy.orm import Session

from backend.repositories.order_repository import OrderRepository
from backend.services.save_handler import SaveHandler
from models.input import OrderInput
from models.order import Order
from bridge.product import orm_product_to_dict

logger = logging.getLogger(__name__)


class OrderBridge:
    """Bridge for order-related save and fetch operations."""

    def __init__(
        self,
        save_handler: SaveHandler,
        session_factory: Callable[[], Session],
    ) -> None:
        self._save_handler = save_handler
        self._session_factory = session_factory

    def save_single_order(self, order: OrderInput) -> bool:
        """Save a single order (with its products) as an upsert."""
        try:
            self._save_handler.save_single_order(order)
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
            return self.orm_order_to_dict(order)
        finally:
            session.close()

    def orm_order_to_dict(self, order: Order) -> Order:
        """Transform an ORM Order entity into an Order dataclass."""
        return Order(
            id=order.ID,
            date=order.DATE.isoformat() if order.DATE else "",
            supplier=order.SUPPLIER,
            nfe_key=order.NFE_KEY or "",
            freight=order.FREIGHT,
            unloading=order.UNLOADING,
            products=[orm_product_to_dict(p) for p in order.products],
        )

