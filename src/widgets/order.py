from __future__ import annotations

import logging
from typing import Any

from backend.injector_module import get_injector
from backend.models.dto import OrderInput
from backend.qml.qml_transformers import dict_to_order_input
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
    orders: list[dict[str, Any]],
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
