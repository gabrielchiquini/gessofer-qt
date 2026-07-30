from __future__ import annotations

# Lazy imports for functions to avoid circular dependencies
from typing import TYPE_CHECKING

from bridge.models.certificate import CertificateInfo
from bridge.models.expense import Expense, ExpenseInput
from bridge.models.order import (
    FreightResult,
    Order,
    OrderSummary,
    XmlImportResult,
)
from bridge.models.product import (
    PageResponse,
    Product,
    ProductListItem,
)
from bridge.models.validation import Validation

if TYPE_CHECKING:
    from bridge.certificate import fetch_certificate_info, save_certificate_from_pfx
    from bridge.expense import fetch_expenses_for_month, save_expenses
    from bridge.order import fetch_order_by_id, save_orders, save_single_order
    from bridge.order_summary import OrderSummary, fetch_order_summaries
    from bridge.product import fetch_orders_for_month, fetch_products

__all__ = [
    "CertificateInfo",
    "ProductListItem",
    "Product",
    "Expense",
    "ExpenseInput",
    "FreightResult",
    "OrderSummary",
    "XmlImportResult",
    "Validation",
    "PageResponse",
    "fetch_products",
    "fetch_orders_for_month",
    "fetch_order_summaries",
    "fetch_order_by_id",
    "save_single_order",
    "save_expenses",
    "fetch_expenses_for_month",
    "fetch_certificate_info",
    "save_certificate_from_pfx",
]
