from __future__ import annotations

from typing import List

from backend.models.dto import OrderInput
from backend.services.save_order_service import SaveOrderService


def save_orders(
    orders: List[OrderInput],
    deleted_orders: List[str],
) -> None:
    """
    Save orders in a single database transaction.

    This function is the API entry point for the 'save_orders' command.
    It delegates all business logic to SaveOrderService.

    Args:
        orders: List of OrderInput DTOs to save.
        deleted_orders: List of order UUIDs to delete.

    Raises:
        ValidationError: If input data fails validation.
        BackendError: If a database or transaction error occurs.
    """
    service = SaveOrderService()
    service.save_orders(orders=orders, deleted_order_ids=deleted_orders)
