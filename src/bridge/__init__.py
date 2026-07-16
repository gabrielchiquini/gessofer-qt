from __future__ import annotations

from bridge.models.expense import ExpenseDict, ExpenseInputDict
from bridge.models.order import (
    FreightResultDict,
    OrderDict,
    OrderInputDict,
    OrderSummaryDict,
    XmlImportResultDict,
)
from bridge.models.product import (
    PageResponseDict,
    ProductDict,
    ProductInputDict,
    ProductListItemDict,
)
from bridge.models.validation import ValidationDict

# Lazy imports for functions to avoid circular dependencies
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bridge.expense import fetch_expenses_for_month, save_expenses
    from bridge.order import fetch_order_by_id, save_orders
    from bridge.order_summary import OrderSummaryDict, fetch_order_summaries
    from bridge.product import fetch_orders_for_month, fetch_products

__all__ = [
    "ProductListItemDict",
    "ProductDict",
    "OrderDict",
    "ExpenseDict",
    "OrderInputDict",
    "ProductInputDict",
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
    "save_orders",
    "save_expenses",
    "fetch_expenses_for_month",
]
