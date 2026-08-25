from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from models.output import Product


@dataclass
class Order:
    """An order entity as returned by orm_order_to_dict."""
    id: str
    date: str  # YYYY-MM-DD
    supplier: str
    nfe_key: str  # changed from nfeKey to snake_case
    freight: int
    unloading: int
    products: List[Product] = field(default_factory=list)


@dataclass
class OrderSummary:
    """An order summary for the list-and-navigate table view."""
    id: str  # order UUID
    date: str  # YYYY-MM-DD (ISO, will be converted to BR in widget)
    supplier: str
    product_count: int
    products_total: int  # cents
    order_total: int  # cents (products + freight + unloading)

@dataclass
class XmlImportResult:
    """Result of an XML import operation."""
    orders: List[Order] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
