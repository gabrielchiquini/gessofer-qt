from __future__ import annotations

import logging
from typing import Callable

from injector import inject
from sqlalchemy.orm import Session

from backend.repositories.order_repository import OrderRepository
from bridge.models.order import Order as OrderDataclass
from bridge.models.product import Product as ProductDataclass, ProductListItem, PageResponse as BridgePageResponse
from backend.utils.date import parse_month_for_orders

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
    ) -> BridgePageResponse[ProductListItem]:
        """Fetch paginated products with optional filters. Returns a BridgePageResponse[ProductListItem]."""
        session: Session = self._session_factory()
        try:
            repo = OrderRepository(session)
            response = repo.search_products(page, supplier, product, month)
            return _product_page_to_dict(response)
        finally:
            session.close()

    def fetch_orders_for_month(self, month: str) -> list[OrderDataclass]:
        """Fetch orders for a month in MM/yyyy format. Returns list of Order dataclass instances."""
        session: Session = self._session_factory()
        try:
            m, y = parse_month_for_orders(month)
            repo = OrderRepository(session)
            orders = repo.fetch_orders_for_month(m, y)
            # Import at call time to avoid circular import with bridge.product
            from bridge.product import orm_order_to_dict
            return [orm_order_to_dict(o) for o in orders]
        finally:
            session.close()


def _product_page_to_dict(response: BridgePageResponse[ProductListItem]) -> BridgePageResponse[ProductListItem]:
    """Transform a PageResponse[Product] into a BridgePageResponse[ProductListItem]."""
    from bridge.product import product_list_item_to_dict
    return BridgePageResponse(
        items=[product_list_item_to_dict(p) for p in response.items],
        page=response.page,
        page_count=response.page_count,
        total=response.total,
        page_size=response.page_size,
    )
