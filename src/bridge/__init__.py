from __future__ import annotations

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
    from bridge.certificate import CertificateBridge
    from bridge.expense import ExpenseBridge
    from bridge.nfe import NfeBridge
    from bridge.order import OrderBridge
    from bridge.order_summary import OrderSummaryBridge
    from bridge.product import ProductBridge

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
    "ProductBridge",
    "OrderBridge",
    "ExpenseBridge",
    "NfeBridge",
    "CertificateBridge",
    "OrderSummaryBridge",
]
