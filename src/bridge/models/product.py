from __future__ import annotations
from typing import Generic, TypeVar

from typing_extensions import TypedDict

T = TypeVar("T")


class PageResponseDict(TypedDict, Generic[T]):
    """Paginated product page response."""

    items: list[T]
    page: int
    page_count: int
    total: int
    page_size: int


class ProductListItemDict(TypedDict):
    """A single product list item as returned by product_page_to_dict / ORM transform."""

    date: str  # dd/MM/yyyy format
    supplier: str
    name: str
    price: str  # formatted string like "R$ 1.234,56"
    totalPrice: str  # formatted string
    orderId: str


class ProductDict(TypedDict):
    """A product entity dict (from orm_product_to_dict)."""

    id: str
    name: str
    quantity: int
    price: int
    total: int
    order_id: str
    itemOrdinal: int | None
