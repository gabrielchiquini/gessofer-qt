from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from backend.injector_module import get_injector
from backend.models.dto import OrderInput
from backend.repositories.order_repository import OrderRepository
from backend.services.save_order_service import SaveOrderService, SaveExpenseService
from bridge.models.order import OrderDict
from bridge.product import orm_order_to_dict, _get_fetch_handler

logger = logging.getLogger(__name__)


class SaveHandler:
    """Wraps SaveOrderService and SaveExpenseService."""

    def __init__(
            self,
            save_order_service: SaveOrderService,
            save_expense_service: SaveExpenseService,
    ) -> None:
        self._save_order_service = save_order_service
        self._save_expense_service = save_expense_service

    def save_orders(
            self,
            orders: list[OrderInput],
            deleted_order_ids: list[str],
    ) -> None:
        """Save orders in a single transaction."""
        self._save_order_service.save_orders(orders, deleted_order_ids)

    def save_single_order(self, order: OrderInput) -> None:
        """Save a single order (with its products) as an upsert."""
        self._save_order_service.save_single_order(order)


_save_handler: SaveHandler | None = None


def _get_save_handler() -> SaveHandler | None:
    """Lazy-initialize the SaveHandler singleton."""
    global _save_handler
    if _save_handler is None:
        injector = get_injector()
        save_order_service = injector.get(SaveOrderService)
        save_expense_service = injector.get(SaveExpenseService)
        _save_handler = SaveHandler(save_order_service, save_expense_service)
    return _save_handler

def save_single_order(order: OrderInput) -> bool:
    """
    Save a single order (with its products) as an upsert.

    If an order with the same ID already exists, it is replaced.
    Otherwise, a new order is created.

    Args:
        order: Order dict to convert and save.

    Returns:
        True on success, False on error.
    """
    try:
        handler = _get_save_handler()
        handler.save_single_order(order)
        return True
    except Exception as exc:
        logger.error("Error in save_single_order: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return False


def fetch_order_by_id(order_id: str) -> OrderDict | None:
    """
    Fetch a single order by UUID, including all products.

    Args:
        order_id: The order UUID.

    Returns:
        OrderDict with products, or None if not found.
    """
    session: Session = _get_fetch_handler()._session_factory()
    try:
        repo = OrderRepository(session)
        order = repo.fetch_order_by_id(order_id)
        if order is None:
            return None
        return orm_order_to_dict(order)
    finally:
        session.close()
