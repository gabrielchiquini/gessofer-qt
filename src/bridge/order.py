from __future__ import annotations

import logging

from typing import cast

from sqlalchemy.orm import Session

from bridge.models.order import OrderDict, OrderInputDict
from bridge.product import orm_order_to_dict, _get_fetch_handler
from backend.entities.orm import Order
from backend.injector_module import get_injector
from backend.models.dto import OrderInput
from backend.repositories.order_repository import OrderRepository
from backend.services.save_order_service import SaveOrderService, SaveExpenseService

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


def dict_to_order_input(d: OrderInputDict) -> OrderInput:
    """Transform a widget-bridge dict (from save/distribute/validate) into an OrderInput DTO."""
    products: list[OrderInput] = []
    for p in d.get("products", []):
        pi = OrderInput(
            id=p.get("id", ""),
            date="",
            supplier="",
            nfe_key="",
            freight=0,
            unloading=0,
            products=[],
        )
        pi.name = p.get("name", "")
        pi.quantity = p.get("quantity", 0)
        pi.price = p.get("price", 0)
        pi.total = p.get("total", 0)
        pi.order_id = p.get("order_id", "")
        pi.item_ordinal = p.get("itemOrdinal")
        products.append(pi)
    return OrderInput(
        id=d.get("id", ""),
        date=d.get("date", ""),
        supplier=d.get("supplier", ""),
        nfe_key=d.get("nfeKey", ""),
        freight=d.get("freight", 0),
        unloading=d.get("unloading", 0),
        products=products,
    )


_save_handler: SaveHandler | None = None


def _get_save_handler() -> SaveHandler:
    """Lazy-initialize the SaveHandler singleton."""
    global _save_handler
    if _save_handler is None:
        injector = get_injector()
        save_order_service = injector.get(SaveOrderService)
        save_expense_service = injector.get(SaveExpenseService)
        _save_handler = SaveHandler(save_order_service, save_expense_service)
    return _save_handler


def save_orders(
    orders: list[OrderInputDict],
    deleted_order_ids: list[str],
) -> bool:
    """
    Save a list of orders and delete specified old orders.

    Args:
        orders: List of order dicts to convert and save.
        deleted_order_ids: List of order UUIDs to delete.

    Returns:
        True on success, False on error.
    """
    try:
        handler = _get_save_handler()
        order_inputs: list[OrderInput] = [dict_to_order_input(o) for o in orders]
        handler.save_orders(order_inputs, deleted_order_ids)
        return True
    except Exception as exc:
        logger.error("Error in save_orders: %s", exc)
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
