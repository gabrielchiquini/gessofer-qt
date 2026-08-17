from __future__ import annotations

# Lazy imports for functions to avoid circular dependencies
from typing import TYPE_CHECKING

from models.certificate import CertificateInfo
from models.input import ExpenseInput
from models.output import ExpenseOutput, ExpensesForMonthOutput
from models.order import (
    FreightResult,
    Order,
    OrderSummary,
    XmlImportResult,
)
from models.output import (
    PageResponse,
    Product,
    ProductListItem,
)
from models.validation import Validation

if TYPE_CHECKING:
    from bridge.certificate import fetch_certificate_info, save_certificate_from_pfx
    from bridge.expense import fetch_expenses_for_month, save_expenses
    from bridge.nfe import search_nfe_key
    from bridge.order import fetch_order_by_id, save_orders, save_single_order
    from models.order import OrderSummary
    from bridge.order_summary import fetch_order_summaries
    from bridge.product import fetch_orders_for_month, fetch_products

__all__ = [
    "CertificateInfo",
    "ProductListItem",
    "Product",
    "ExpenseOutput",
    "ExpenseInput",
    "ExpensesForMonthOutput",
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
    "search_nfe_key",
]
