from __future__ import annotations

import logging

from bridge.models.order import Order, OrderSummary


logger = logging.getLogger(__name__)


def fetch_order_summaries(month: str) -> list[OrderSummary]:
    """
    Fetch order summaries for a given month.

    Args:
        month: Month in MM/yyyy format (e.g., "07/2026").

    Returns:
        List of OrderSummary dataclass instances. On error, returns [].
    """
    from bridge.product import fetch_orders_for_month

    try:
        orders: list[Order] = fetch_orders_for_month(month)
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
