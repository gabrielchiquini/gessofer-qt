from __future__ import annotations

import logging
from typing import Callable

from injector import inject
from sqlalchemy.orm import Session

from bridge.models.order import Order as OrderDataclass
from bridge.models.product import Product as ProductDataclass, ProductListItem, PageResponse as BridgePageResponse
from backend.database.connection import get_engine
from backend.injector_module import get_injector
from backend.models.dto import PageResponse
from backend.entities.orm import Order, Product
from backend.utils.currency import cents_to_display
from backend.utils.date import datetime_to_br_date
from backend.repositories.order_repository import OrderRepository
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
            return product_page_to_dict(response)
        finally:
            session.close()

    def fetch_orders_for_month(self, month: str) -> list[OrderDataclass]:
        """Fetch orders for a month in MM/yyyy format. Returns list of Order dataclass instances."""
        session: Session = self._session_factory()
        try:
            m, y = parse_month_for_orders(month)
            repo = OrderRepository(session)
            orders = repo.fetch_orders_for_month(m, y)
            return [orm_order_to_dict(o) for o in orders]
        finally:
            session.close()


def orm_product_to_dict(product: Product) -> ProductDataclass:
    """Transform an ORM Product entity into a Product dataclass."""
    return ProductDataclass(
        id=product.ID,
        name=product.NAME,
        quantity=product.QUANTITY,
        price=product.PRICE,
        total=product.TOTAL_PRICE,
        order_id=product.ORDER_ID,
        item_ordinal=product.ITEM_ORDINAL,
    )


def orm_order_to_dict(order: Order) -> OrderDataclass:
    """Transform an ORM Order entity into an Order dataclass."""
    return OrderDataclass(
        id=order.ID,
        date=order.DATE.isoformat() if order.DATE else "",
        supplier=order.SUPPLIER,
        nfe_key=order.NFE_KEY or "",
        freight=order.FREIGHT,
        unloading=order.UNLOADING,
        products=[orm_product_to_dict(p) for p in order.products],
    )


def product_list_item_to_dict(product: Product) -> ProductListItem:
    """Transform an ORM Product entity into a ProductListItem dataclass."""
    date_str = datetime_to_br_date(product.order.DATE)
    return ProductListItem(
        date=date_str,
        supplier=product.order.SUPPLIER if product.order else "",
        name=product.NAME,
        price=cents_to_display(product.PRICE),
        total_price=cents_to_display(product.TOTAL_PRICE),
        order_id=product.ORDER_ID,
    )


def product_page_to_dict(response: PageResponse[Product]) -> BridgePageResponse[ProductListItem]:
    """Transform a PageResponse[Product] into a BridgePageResponse[ProductListItem]."""
    return BridgePageResponse(
        items=[product_list_item_to_dict(p) for p in response.items],
        page=response.page,
        page_count=response.page_count,
        total=response.total,
        page_size=response.page_size,
    )


_fetch_handler: FetchHandler | None = None


def _get_fetch_handler() -> FetchHandler:
    """Lazy-initialize the FetchHandler singleton."""
    global _fetch_handler
    if _fetch_handler is None:
        injector = get_injector()
        _fetch_handler = injector.get(FetchHandler)
    return _fetch_handler


def fetch_products(
    page: int,
    supplier: str = "",
    product: str = "",
    month: str = "",
) -> BridgePageResponse[ProductListItem]:
    """
    Fetch paginated product list with optional filters.

    Args:
        page: Page number (1-based).
        supplier: Optional supplier name filter.
        product: Optional product name filter.
        month: Optional month filter in MM/yyyy format.

    Returns:
        BridgePageResponse[ProductListItem] with paginated product data.
        On error, returns an empty-page response.
    """
    try:
        handler = _get_fetch_handler()
        return handler.fetch_products(
            page,
            supplier or None,
            product or None,
            month or None,
        )
    except Exception as exc:
        logger.error("Error in fetch_products: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return BridgePageResponse(
            items=[],
            page=page,
            page_count=0,
            total=0,
            page_size=50,
        )


def fetch_orders_for_month(month: str) -> list[OrderDataclass]:
    """
    Fetch all orders for a given month.

    Args:
        month: Month in MM/yyyy format.

    Returns:
        List of Order dataclass instances. On error, returns [].
    """
    try:
        handler = _get_fetch_handler()
        return handler.fetch_orders_for_month(month)
    except Exception as exc:
        logger.error("Error in fetch_orders_for_month: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return []
