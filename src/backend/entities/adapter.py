from __future__ import annotations

from backend.entities.orm import OrderEntity, ProductEntity
from models.order import Order
from models.output import Product


def orm_product_to_model(product: ProductEntity) -> Product:
    """Transform an ORM Product entity into a Product dataclass."""
    return Product(
        id=product.ID,
        name=product.NAME,
        quantity=product.QUANTITY,
        price=product.PRICE,
        price_with_freight=product.PRICE_WITH_FREIGHT,
        total=product.TOTAL_PRICE,
        order_id=product.ORDER_ID,
        item_ordinal=product.ITEM_ORDINAL,
    )


def orm_order_to_model(order: OrderEntity) -> Order:
    """Transform an ORM Order entity into an Order dataclass."""
    return Order(
        id=order.ID,
        date=order.DATE.isoformat() if order.DATE else "",
        supplier=order.SUPPLIER,
        nfe_key=order.NFE_KEY or "",
        freight=order.FREIGHT,
        unloading=order.UNLOADING,
        products=[orm_product_to_model(p) for p in order.products],
    )
