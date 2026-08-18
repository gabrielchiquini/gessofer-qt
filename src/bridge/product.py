from __future__ import annotations

import logging

from backend.entities.orm import Order, Product
from backend.services.fetch_handler import FetchHandler
from backend.utils.currency import cents_to_display
from backend.utils.date import datetime_to_br_date
from models.order import Order as OrderDataclass
from models.output import Product as ProductDataclass, ProductListItem, PageResponse as BridgePageResponse

logger = logging.getLogger(__name__)


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


class ProductBridge:
    """Bridge for product-related fetch operations."""

    def __init__(self, fetch_handler: FetchHandler) -> None:
        self._fetch_handler = fetch_handler

    def fetch_products(
        self,
        page: int,
        supplier: str = "",
        product: str = "",
        month: str = "",
    ) -> BridgePageResponse[ProductListItem]:
        """Fetch paginated product list with optional filters."""
        try:
            return self._fetch_handler.fetch_products(
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

    def fetch_orders_for_month(self, month: str) -> list[OrderDataclass]:
        """Fetch all orders for a given month."""
        try:
            return self._fetch_handler.fetch_orders_for_month(month)
        except Exception as exc:
            logger.error("Error in fetch_orders_for_month: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return []


# ── Backward-compatible re-exports ──────────────────────────────
# These delegate to the DI-registered ProductBridge singleton.
# They will be removed once frontend widgets use ProductBridge directly.


def _get_product_bridge() -> ProductBridge:
    """Lazy-access the DI-registered ProductBridge singleton."""
    from injector_module import get_injector
    return get_injector().get(ProductBridge)


def fetch_products(
    page: int,
    supplier: str = "",
    product: str = "",
    month: str = "",
) -> BridgePageResponse[ProductListItem]:
    """Backward-compatible: delegates to ProductBridge.fetch_products()."""
    return _get_product_bridge().fetch_products(page, supplier, product, month)


def fetch_orders_for_month(month: str) -> list[OrderDataclass]:
    """Backward-compatible: delegates to ProductBridge.fetch_orders_for_month()."""
    return _get_product_bridge().fetch_orders_for_month(month)
