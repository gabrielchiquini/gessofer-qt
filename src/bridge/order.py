from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy.orm import Session

from backend.injector_module import get_injector
from models import OrderInput
from backend.repositories.order_repository import OrderRepository
from backend.services.save_handler import SaveHandler
from models.order import Order
from bridge.product import orm_order_to_dict

logger = logging.getLogger(__name__)


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
        handler = get_injector().get(SaveHandler)
        handler.save_single_order(order)
        return True
    except Exception as exc:
        logger.error("Error in save_single_order: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return False


def fetch_order_by_id(order_id: str) -> Order | None:
    """
    Fetch a single order by UUID, including all products.

    Args:
        order_id: The order UUID.

    Returns:
        Order dataclass with products, or None if not found.
    """
    session_factory = get_injector().get(Callable[[], Session])
    session: Session = session_factory()
    try:
        repo = OrderRepository(session)
        order = repo.fetch_order_by_id(order_id)
        if order is None:
            return None
        return orm_order_to_dict(order)
    finally:
        session.close()
