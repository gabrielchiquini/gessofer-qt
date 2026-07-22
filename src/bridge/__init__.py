from __future__ import annotations

# Lazy imports for functions to avoid circular dependencies
from typing import TYPE_CHECKING

from bridge.models.expense import ExpenseDict, ExpenseInputDict
from bridge.models.order import (
    FreightResultDict,
    OrderSummaryDict,
    XmlImportResultDict,
)
from bridge.models.product import (
    PageResponseDict,
    ProductDict,
    ProductListItemDict,
)
from bridge.models.validation import ValidationDict

if TYPE_CHECKING:
    from bridge.expense import fetch_expenses_for_month, save_expenses
    from bridge.order import fetch_order_by_id, save_orders, save_single_order
    from bridge.order_summary import OrderSummaryDict, fetch_order_summaries
    from bridge.product import fetch_orders_for_month, fetch_products

__all__ = [
    "ProductListItemDict",
    "ProductDict",
    "ExpenseDict",
    "ExpenseInputDict",
    "FreightResultDict",
    "OrderSummaryDict",
    "XmlImportResultDict",
    "ValidationDict",
    "PageResponseDict",
    "fetch_products",
    "fetch_orders_for_month",
    "fetch_order_summaries",
    "fetch_order_by_id",
    "save_single_order",
    "save_expenses",
    "fetch_expenses_for_month",
]
