from __future__ import annotations

from backend.models.dto import ExpenseInput, OrderInput
from backend.services.save_order_service import SaveExpenseService, SaveOrderService
from backend.utils.date import parse_month_for_expenses


class SaveHandler:
    """Handles all save operations for the QML layer."""

    def __init__(
        self,
        save_order_service: SaveOrderService,
        save_expense_service: SaveExpenseService,
    ) -> None:
        self._save_order_service = save_order_service
        self._save_expense_service = save_expense_service

    def save_orders(self, orders: list[OrderInput], deleted_orders: list[str]) -> None:
        """Delegate to SaveOrderService."""
        self._save_order_service.save_orders(orders=orders, deleted_order_ids=deleted_orders)

    def save_expenses(self, expenses: list[ExpenseInput], month: str) -> None:
        """Delegate to SaveExpenseService."""
        validated = parse_month_for_expenses(month)
        self._save_expense_service.save_expenses(expenses=expenses, month=validated)
