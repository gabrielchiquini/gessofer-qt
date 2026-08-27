from __future__ import annotations

import logging
from typing import Callable

from injector import inject
from sqlalchemy.orm import Session

from backend.entities.adapter import orm_order_to_model
from backend.entities.orm import ProductEntity, OrderEntity
from backend.repositories.order_repository import OrderRepository
from backend.utils.currency import cents_to_display
from backend.utils.date import parse_month_for_orders, datetime_to_br_date
from models.order import Order
from models.output import Product, ProductListItem, PageResponse

logger = logging.getLogger(__name__)


class FetchHandler:
    """Wraps OrderRepository to provide fetch operations."""

    @inject
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def fetch_products(
            self,
            page: int,
            supplier: str | None = None,
            product: str | None = None,
            month: str | None = None,
    ) -> PageResponse[ProductListItem]:
        """Fetch paginated products with optional filters. Returns a BridgePageResponse[ProductListItem]."""
        session: Session = self._session_factory()
        try:
            repo = OrderRepository(session)
            response = repo.search_products(page, supplier, product, month)
            return _product_page_to_dict(response)
        finally:
            session.close()

    def fetch_orders_for_month(self, month: str) -> list[Order]:
        """Fetch orders for a month in MM/yyyy format. Returns list of Order dataclass instances."""
        session: Session = self._session_factory()
        try:
            m, y = parse_month_for_orders(month)
            repo = OrderRepository(session)
            orders = repo.fetch_orders_for_month(m, y)
            return [orm_order_to_model(o) for o in orders]
        finally:
            session.close()


def _product_page_to_dict(response: PageResponse[ProductEntity]) -> PageResponse[ProductListItem]:
    """Transform a PageResponse[Product] into a BridgePageResponse[ProductListItem]."""
    return PageResponse(
        items=[product_list_item_to_dict(p) for p in response.items],
        page=response.page,
        page_count=response.page_count,
        total=response.total,
        page_size=response.page_size,
    )


def product_list_item_to_dict(product: ProductEntity) -> ProductListItem:
    """Transform an ORM Product entity into a ProductListItem dataclass."""
    date_str = datetime_to_br_date(product.order.DATE)
    return ProductListItem(
        date=date_str,
        supplier=product.order.SUPPLIER if product.order else "",
        name=product.NAME,
        price=cents_to_display(product.PRICE),
        price_with_freight=cents_to_display(product.PRICE_WITH_FREIGHT),
        total_price=cents_to_display(product.TOTAL_PRICE),
        order_id=product.ORDER_ID,
    )
