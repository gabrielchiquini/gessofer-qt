from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.injector_module import get_injector
from backend.models.dto import PageResponse
from backend.utils.transformers import product_page_to_dict, orm_order_to_dict
from backend.repositories.order_repository import OrderRepository
from backend.utils.date import parse_month_for_orders

logger = logging.getLogger(__name__)


class FetchHandler:
    """Wraps OrderRepository to provide fetch operations."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def fetch_products(
        self,
        page: int,
        supplier: str | None = None,
        product: str | None = None,
        month: str | None = None,
    ) -> dict[str, Any]:
        """Fetch paginated products with optional filters. Returns dict compatible with QML product_page_to_dict output."""
        session: Session = self._session_factory()
        try:
            repo = OrderRepository(session)
            response = repo.search_products(page, supplier, product, month)
            return product_page_to_dict(response)
        except Exception as exc:
            logger.error("Error fetching products: %s", exc)
            raise
        finally:
            session.close()

    def fetch_orders_for_month(self, month: str) -> list[dict[str, Any]]:
        """Fetch orders for a month in MM/yyyy format. Returns list of order dicts."""
        session: Session = self._session_factory()
        try:
            m, y = parse_month_for_orders(month)
            repo = OrderRepository(session)
            orders = repo.fetch_orders_for_month(str(m).zfill(2), y)
            return [orm_order_to_dict(o) for o in orders]
        except Exception as exc:
            logger.error("Error fetching orders: %s", exc)
            raise
        finally:
            session.close()


_fetch_handler: FetchHandler | None = None
_session_factory: Callable[[], Session] | None = None


def _get_fetch_handler() -> FetchHandler:
    """Lazy-initialize the FetchHandler singleton."""
    global _fetch_handler, _session_factory
    if _fetch_handler is None:
        injector = get_injector()
        engine = get_engine()
        from sqlalchemy import create_engine
        from sqlalchemy.pool import StaticPool

        # Create a session factory bound to the same engine
        def _session_factory() -> Session:
            from sqlalchemy.orm import Session as SA_Session
            return SA_Session(engine)

        _session_factory = _session_factory
        _fetch_handler = FetchHandler(_session_factory)
    return _fetch_handler


def fetch_products(
    page: int,
    supplier: str = "",
    product: str = "",
    month: str = "",
) -> dict[str, Any]:
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


def fetch_orders_for_month(month: str) -> list[dict[str, Any]]:
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
