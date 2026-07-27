from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, List

T = TypeVar("T")


@dataclass
class PageResponse(Generic[T]):
    """Paginated response as returned by product_page_to_dict."""
    items: List[T]
    page: int
    page_count: int
    total: int
    page_size: int


@dataclass
class ProductListItem:
    """A single product list item as returned by product_page_to_dict / ORM transform."""
    date: str  # dd/MM/yyyy format
    supplier: str
    name: str
    price: str  # formatted string like "R$ 1.234,56"
    total_price: str  # formatted string
    order_id: str


@dataclass
class Product:
    """A product entity as returned by orm_product_to_dict."""
    id: str
    name: str
    quantity: int
    price: int
    total: int
    order_id: str
    item_ordinal: int | None = None
