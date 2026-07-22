from __future__ import annotations

from typing import TypedDict

from bridge.models.product import ProductDict


class OrderDict(TypedDict):
    """An order entity dict (from orm_order_to_dict)."""

    id: str
    date: str  # YYYY-MM-DD
    supplier: str
    nfeKey: str
    freight: int
    unloading: int
    products: list[ProductDict]


class OrderSummaryDict(TypedDict):
    """An order summary for the list-and-navigate table view."""

    id: str  # order UUID
    date: str  # YYYY-MM-DD (ISO, will be converted to BR in widget)
    supplier: str
    product_count: int
    products_total: int  # cents
    order_total: int  # cents (products + freight + unloading)


class FreightResultDict(TypedDict):
    """Result of a freight distribution calculation as a dict."""

    order_id: str
    old_freight: int
    old_unloading: int
    ratio: float
    products_total_before: int
    products_total_after: int
    new_products: list[ProductDict]


class XmlImportResultDict(TypedDict):
    """Result of an XML import operation as a dict."""

    orders: list[OrderDict]
    warnings: list[str]
