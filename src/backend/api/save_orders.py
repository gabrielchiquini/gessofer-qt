from __future__ import annotations

from typing import Callable, List

from backend.injector_module import call_with_injection

from backend.models.dto import OrderInput
from backend.services.save_order_service import SaveOrderService


def save_orders(
    orders: List[OrderInput],
    deleted_orders: List[str],
    service: SaveOrderService,
) -> None:
    """
    Save orders in a single database transaction.

    This function is the API entry point for the 'save_orders' command.
    It delegates all business logic to SaveOrderService.

    Args:
        orders: List of OrderInput DTOs to save.
        deleted_orders: List of order UUIDs to delete.
        service: Injected SaveOrderService instance.

    Raises:
        ValidationError: If input data fails validation.
        DatabaseError: If a database or transaction error occurs.
    """
    service.save_orders(orders=orders, deleted_order_ids=deleted_orders)


# Wrap function with injection
def _save_orders_injected(
    orders: List[OrderInput],
    deleted_orders: List[str],
) -> None:
    """Injected wrapper for save_orders."""
    call_with_injection(save_orders, orders, deleted_orders)


def get_save_orders_injected() -> Callable[[List[OrderInput], List[str]], None]:
    """Return the injected version of save_orders for BackendManager."""
    return _save_orders_injected
