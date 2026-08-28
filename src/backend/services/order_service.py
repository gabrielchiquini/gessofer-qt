from __future__ import annotations

import logging
from typing import Callable

from injector import inject
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.entities.adapter import orm_order_to_model
from backend.entities.orm import ProductEntity, OrderEntity
from backend.repositories.order_repository import OrderRepository
from backend.utils.currency import cents_to_input, cents_to_view
from backend.utils.date import parse_month_for_orders, datetime_to_br_date
from backend.errors import DatabaseError
from models.input import OrderInput
from models.order import Order, OrderSummary
from models.output import Product, ProductListItem, PageResponse

logger = logging.getLogger(__name__)


class OrderService:
    """Unified service for order fetch and save operations.

    Merges the responsibilities of the former FetchHandler, SaveOrderService,
    ProductBridge, OrderBridge, and OrderSummaryBridge into a single class:
    - fetch_products: paginated product search with optional filters.
    - fetch_orders_for_month: list of Order dataclass instances for a month.
    - save_single_order: upsert a single order (with its products) in one transaction.
    - fetch_order_by_id: fetch a single order by UUID including all products.
    - delete_order: delete an order and its associated products.
    - fetch_order_summaries: compute summaries for orders in a given month.

    Dependencies:
    - engine: Engine (for save operations using Session context manager)
    - session_factory: Callable returning Session (for fetch operations)
    """

    @inject
    def __init__(
        self,
        engine: Engine,
        session_factory: Callable[[], Session],
    ) -> None:
        self._engine = engine
        self._session_factory = session_factory

    # ── Fetch operations (from FetchHandler) ───────────────────────

    def fetch_products(
        self,
        page: int,
        supplier: str | None = None,
        product: str | None = None,
        month: str | None = None,
    ) -> PageResponse[ProductListItem]:
        """Fetch paginated products with optional filters. Returns empty PageResponse on error."""
        try:
            session: Session = self._session_factory()
            try:
                repo = OrderRepository(session)
                response = repo.search_products(page, supplier, product, month)
                return _product_page_to_dict(response)
            finally:
                session.close()
        except Exception as exc:
            logger.error("Error in fetch_products: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return PageResponse(
                items=[], page=page, page_count=0, total=0, page_size=50,
            )

    def fetch_orders_for_month(self, month: str) -> list[Order]:
        """Fetch orders for a month in MM/yyyy format. Returns [] on error."""
        try:
            session: Session = self._session_factory()
            try:
                m, y = parse_month_for_orders(month)
                repo = OrderRepository(session)
                orders = repo.fetch_orders_for_month(m, y)
                return [orm_order_to_model(o) for o in orders]
            finally:
                session.close()
        except Exception as exc:
            logger.error("Error in fetch_orders_for_month: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return []

    # ── Save operations (from SaveOrderService) ────────────────────

    def save_single_order(self, order: OrderInput) -> bool:
        """Save a single order (with its products) as an upsert.

        If an order with the same ID already exists, its products and order row
        are deleted first, then the new data is inserted — all in one transaction.

        Returns True on success, False on failure.
        """
        with Session(self._engine) as session:
            try:
                repo = OrderRepository(session)

                # Delete existing order + products (scoped to this single order)
                if order.id is not None:
                    repo.delete_order_products([order.id])
                    repo.delete_orders([order.id])

                # Insert the order
                repo.insert_order(order)

                # Insert the products
                for product in order.products:
                    repo.insert_product(product)

                session.commit()
                return True
            except Exception as exc:
                logger.error("Erro ao salvar pedido: %s", exc)
                return False

    # ── Merged from ProductBridge, OrderBridge, OrderSummaryBridge ─

    def fetch_order_by_id(self, order_id: str) -> Order | None:
        """Fetch a single order by UUID, including all products."""
        session: Session = self._session_factory()
        try:
            repo = OrderRepository(session)
            order = repo.fetch_order_by_id(order_id)
            if order is None:
                return None
            return orm_order_to_model(order)
        finally:
            session.close()

    def delete_order(self, order_id: str) -> bool:
        """Delete an order and its associated products. Returns True on success, False on failure."""
        try:
            session: Session = self._session_factory()
            try:
                repo = OrderRepository(session)
                repo.delete_order_products([order_id])
                repo.delete_orders([order_id])
                session.commit()
                return True
            finally:
                session.close()
        except Exception as exc:
            logger.error("Error in delete_order: %s", exc)
            return False

    def fetch_order_summaries(self, month: str) -> list[OrderSummary]:
        """Fetch order summaries for a given month."""
        try:
            orders: list[Order] = self.fetch_orders_for_month(month)
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


# ── Helper functions (from FetchHandler module-level) ──────────────

def _product_page_to_dict(
    response: PageResponse[ProductEntity],
) -> PageResponse[ProductListItem]:
    """Transform a PageResponse[ProductEntity] into a PageResponse[ProductListItem]."""
    return PageResponse(
        items=[product_list_item_to_dict(p) for p in response.items],
        page=response.page,
        page_count=response.page_count,
        total=response.total,
        page_size=response.page_size,
    )


def product_list_item_to_dict(product: ProductEntity) -> ProductListItem:
    """Transform an ORM ProductEntity into a ProductListItem dataclass."""
    date_str = datetime_to_br_date(product.order.DATE)
    return ProductListItem(
        date=date_str,
        supplier=product.order.SUPPLIER if product.order else "",
        name=product.NAME,
        price=cents_to_view(product.PRICE),
        price_with_freight=cents_to_view(product.PRICE_WITH_FREIGHT),
        total_price=cents_to_view(product.TOTAL_PRICE),
        order_id=product.ORDER_ID,
    )
