from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from models.input import OrderInput, ProductInput

logger = logging.getLogger(__name__)


@dataclass
class FreightDistributionResult:
    """Result of a freight distribution calculation."""
    order_id: str
    old_freight: int
    old_unloading: int
    new_products: List[ProductInput]
    ratio: float
    products_total_before: int
    products_total_after: int


class FreightDistributionService:
    """
    Implements the proportional freight/unloading cost allocation algorithm.

    The algorithm redistributes freight + unloading costs across all products
    in an order proportionally to their total values.

    Key constraint: Only the unit PRICE is updated. The TOTAL for each product
    remains unchanged (total = price_before × quantity, used in the ratio
    calculation).
    """

    def distribute(
        self,
        order: OrderInput,
    ) -> FreightDistributionResult:
        """
        Distribute freight and unloading costs across all products in an order.

        Args:
            order: OrderInput with freight, unloading, and products.

        Returns:
            FreightDistributionResult with updated product prices and metadata.

        Raises:
            ValueError: If the order has no products or productsTotal is zero.
        """
        if not order.products:
            raise ValueError("Distribuição de frete requer pelo menos um produto.")

        products_total = sum(p.total for p in order.products)

        if products_total == 0:
            raise ValueError(
                "Distribuição de frete impossível: total de produtos é zero."
            )

        freight_total = order.freight + order.unloading
        ratio = (freight_total + products_total) / products_total

        new_products: list[ProductInput] = []
        for product in order.products:
            if product.quantity == 0:
                # Avoid division by zero — keep original price
                new_price = product.price
            else:
                new_price = round((product.total * ratio) / product.quantity)

            new_products.append(
                ProductInput(
                    id=product.id,
                    name=product.name,
                    quantity=product.quantity,
                    price=new_price,
                    total=product.total,  # Total remains unchanged
                    order_id=product.order_id,
                    item_ordinal=product.item_ordinal,
                )
            )

        products_total_after = sum(p.total for p in new_products)

        return FreightDistributionResult(
            order_id=order.id,
            old_freight=order.freight,
            old_unloading=order.unloading,
            new_products=new_products,
            ratio=ratio,
            products_total_before=products_total,
            products_total_after=products_total_after,
        )

    def apply_to_order(
        self,
        order: OrderInput,
    ) -> OrderInput:
        """
        Apply freight distribution to an order and return a new OrderInput.

        This is a convenience method that calls distribute() and returns
        a new OrderInput with the updated products.

        Args:
            order: OrderInput with freight, unloading, and products.

        Returns:
            A new OrderInput with updated product prices.
        """
        result = self.distribute(order)
        return OrderInput(
            id=result.order_id,
            date="",
            supplier="",
            nfe_key="",
            freight=result.old_freight,
            unloading=result.old_unloading,
            products=result.new_products,
        )
