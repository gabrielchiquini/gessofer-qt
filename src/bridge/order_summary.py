from __future__ import annotations

import logging

from models.order import Order, OrderSummary
from bridge.product import ProductBridge

logger = logging.getLogger(__name__)


class OrderSummaryBridge:
    """Bridge for order summary operations."""

    def __init__(self, product_bridge: ProductBridge) -> None:
        self._product_bridge = product_bridge

    def fetch_order_summaries(self, month: str) -> list[OrderSummary]:
        """Fetch order summaries for a given month."""
        try:
            orders: list[Order] = self._product_bridge.fetch_orders_for_month(month)
            summaries: list[OrderSummary] = []
            for order in orders:
                products_total: int = sum(p.total for p in order.products)
                order_total: int = products_total + order.freight + order.unloading
                summaries.append(
                    OrderSummary(
                        id=order.id,
                        date=order.date,
                        supplier=order.supplier,
                        product_count=len(order.products),
                        products_total=products_total,
                        order_total=order_total,
                    )
                )
            return summaries
        except Exception as exc:
            logger.error("Error in fetch_order_summaries: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return []

