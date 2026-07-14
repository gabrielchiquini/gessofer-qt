from __future__ import annotations

from typing_extensions import TypedDict


class ProductListItemDict(TypedDict):
    """A single product list item as returned by product_page_to_dict / ORM transform."""

    date: str  # dd/MM/yyyy format
    supplier: str
    name: str
    price: str  # formatted string like "R$ 1.234,56"
    totalPrice: str  # formatted string
    orderId: str


class ProductPageResponseDict(TypedDict):
    """Paginated product page response."""

    items: list[ProductListItemDict]
    page: int
    page_count: int
    total: int
    page_size: int


class ProductDict(TypedDict):
    """A product entity dict (from orm_product_to_dict)."""

    id: str
    name: str
    quantity: int
    price: int
    total: int
    order_id: str
    itemOrdinal: int | None


class OrderDict(TypedDict):
    """An order entity dict (from orm_order_to_dict)."""

    id: str
    date: str  # YYYY-MM-DD
    supplier: str
    nfeKey: str
    freight: int
    unloading: int
    products: list[ProductDict]


class ExpenseDict(TypedDict):
    """An expense entity dict (from expense_to_dict)."""

    id: int
    month: str
    description: str
    value: int


class OrderInputDict(TypedDict):
    """Order dict accepted by save_orders bridge function."""

    id: str
    date: str
    supplier: str
    nfeKey: str
    freight: int
    unloading: int
    products: list[ProductInputDict]


class ProductInputDict(TypedDict):
    """Product dict inside an OrderInputDict."""

    id: str
    name: str
    quantity: int
    price: int
    total: int
    order_id: str
    itemOrdinal: int | None


class ExpenseInputDict(TypedDict, total=False):
    """Expense dict accepted by save_expenses bridge function.

    Only 'description' and 'value' are required.
    """

    description: str
    value: int


class FreightResultProductDict(TypedDict):
    """Product dict inside a freight distribution result."""

    id: str
    name: str
    quantity: int
    price: int
    total: int
    order_id: str
    itemOrdinal: int | None


class FreightResultDict(TypedDict):
    """Result of a freight distribution calculation as a dict."""

    order_id: str
    old_freight: int
    old_unloading: int
    ratio: float
    products_total_before: int
    products_total_after: int
    new_products: list[FreightResultProductDict]


class XmlImportProductDict(TypedDict):
    """Product dict inside an XML import result."""

    id: str
    name: str
    quantity: int
    price: int
    total: int
    order_id: str
    itemOrdinal: int | None


class XmlImportOrderDict(TypedDict):
    """Order dict inside an XML import result."""

    id: str
    date: str
    supplier: str
    nfeKey: str
    freight: int
    unloading: int
    products: list[XmlImportProductDict]


class XmlImportResultDict(TypedDict):
    """Result of an XML import operation as a dict."""

    orders: list[XmlImportOrderDict]
    warnings: list[str]


class ValidationDict(TypedDict):
    """Result of a validation operation as a dict."""

    valid: bool
    errors: list[str]


__all__ = [
    "ProductListItemDict",
    "ProductPageResponseDict",
    "ProductDict",
    "OrderDict",
    "ExpenseDict",
    "OrderInputDict",
    "ProductInputDict",
    "ExpenseInputDict",
    "FreightResultProductDict",
    "FreightResultDict",
    "XmlImportProductDict",
    "XmlImportOrderDict",
    "XmlImportResultDict",
    "ValidationDict",
]
