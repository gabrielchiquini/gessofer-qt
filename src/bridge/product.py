from __future__ import annotations

import logging
from typing import Callable

from injector import inject
from sqlalchemy.orm import Session

from bridge import OrderDict, ProductDict, ProductListItemDict, PageResponseDict
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
    ) -> PageResponseDict[ProductListItemDict]:
        """Fetch paginated products with optional filters. Returns bridge-compatible product page response."""
        session: Session = self._session_factory()
        try:
            repo = OrderRepository(session)
            response = repo.search_products(page, supplier, product, month)
            return product_page_to_dict(response)
        finally:
            session.close()

    def fetch_orders_for_month(self, month: str) -> list[OrderDict]:
        """Fetch orders for a month in MM/yyyy format. Returns list of order dicts."""
        session: Session = self._session_factory()
        try:
            m, y = parse_month_for_orders(month)
            repo = OrderRepository(session)
            orders = repo.fetch_orders_for_month(str(m).zfill(2), y)
            return [orm_order_to_dict(o) for o in orders]
        finally:
            session.close()


def orm_product_to_dict(product: Product) -> ProductDict:
    """Transform an ORM Product entity into a bridge-compatible dict."""
    return {
        "id": product.ID,
        "name": product.NAME,
        "quantity": product.QUANTITY,
        "price": product.PRICE,
        "total": product.TOTAL_PRICE,
        "order_id": product.ORDER_ID,
        "itemOrdinal": product.ITEM_ORDINAL,
    }


def orm_order_to_dict(order: Order) -> OrderDict:
    """Transform an ORM Order entity into a bridge-compatible dict."""
    return {
        "id": order.ID,
        "date": order.DATE.isoformat() if order.DATE else "",
        "supplier": order.SUPPLIER,
        "nfeKey": order.NFE_KEY or "",
        "freight": order.FREIGHT,
        "unloading": order.UNLOADING,
        "products": [orm_product_to_dict(p) for p in order.products],
    }


def product_list_item_to_dict(product: Product) -> ProductListItemDict:
    """Transform an ORM Product entity into a dict for the widget bridge Product List table."""
    date_str = datetime_to_br_date(product.order.DATE)
    return {
        "date": date_str,
        "supplier": product.order.SUPPLIER if product.order else "",
        "name": product.NAME,
        "price": cents_to_display(product.PRICE),
        "totalPrice": cents_to_display(product.TOTAL_PRICE),
        "orderId": product.ORDER_ID,
    }


def product_page_to_dict(response: PageResponse[Product]) -> PageResponseDict[ProductListItemDict]:
    """Transform a PageResponse[Product] into a bridge-compatible dict."""
    return {
        "items": [product_list_item_to_dict(p) for p in response.items],
        "page": response.page,
        "page_count": response.page_count,
        "total": response.total,
        "page_size": response.page_size,
    }


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
) -> PageResponseDict[ProductListItemDict]:
    """
    Fetch paginated product list with optional filters.

    Args:
        page: Page number (1-based).
        supplier: Optional supplier name filter.
        product: Optional product name filter.
        month: Optional month filter in MM/yyyy format.

    Returns:
        Dict with keys: items, page, page_count, total, page_size.
        On error, returns an empty-page dict.
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
        return {
            "items": [],
            "page": page,
            "page_count": 0,
            "total": 0,
            "page_size": 50,
        }


def fetch_orders_for_month(month: str) -> list[OrderDict]:
    """
    Fetch all orders for a given month.

    Args:
        month: Month in MM/yyyy format.

    Returns:
        List of order dicts. On error, returns [].
    """
    try:
        handler = _get_fetch_handler()
        return handler.fetch_orders_for_month(month)
    except Exception as exc:
        logger.error("Error in fetch_orders_for_month: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return []
