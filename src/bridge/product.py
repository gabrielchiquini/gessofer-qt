from __future__ import annotations

import logging

from backend.services.order_service import OrderService
from models.order import Order
from models.output import ProductListItem, PageResponse as BridgePageResponse

logger = logging.getLogger(__name__)


class ProductBridge:
    """Bridge for product-related fetch operations."""

    def __init__(self, order_service: OrderService) -> None:
        self._order_service = order_service

    def fetch_products(
            self,
            page: int,
            supplier: str = "",
            product: str = "",
            month: str = "",
    ) -> BridgePageResponse[ProductListItem]:
        """Fetch paginated product list with optional filters."""
        try:
            return self._order_service.fetch_products(
                page,
                supplier or None,
                product or None,
                month or None,
            )
        except Exception as exc:
            logger.error("Error in fetch_products: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return BridgePageResponse(
                items=[], page=page, page_count=0, total=0, page_size=50,
            )

    def fetch_orders_for_month(self, month: str) -> list[Order]:
        """Fetch all orders for a given month."""
        try:
            return self._order_service.fetch_orders_for_month(month)
        except Exception as exc:
            logger.error("Error in fetch_orders_for_month: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return []
