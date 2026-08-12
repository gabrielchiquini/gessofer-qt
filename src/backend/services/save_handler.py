from __future__ import annotations

import logging

from injector import inject

from models import OrderInput
from backend.services.save_order_service import SaveOrderService, SaveExpenseService

logger = logging.getLogger(__name__)


class SaveHandler:
    """Wraps SaveOrderService and SaveExpenseService."""

    @inject
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
