from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import List, Optional, Sequence, cast

from sqlalchemy import func, select, delete
from sqlalchemy.orm import Session, selectinload

from backend.entities.orm import Order, Product
from models import OrderInput, ProductInput, PageResponse
from backend.utils.text import normalize_text


PAGE_SIZE: int = 50


class OrderRepository:
    """Repository for ORDER and PRODUCT tables using SQLAlchemy 2.0."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Query: fetch_orders_for_month ───────────────────────────────

    def fetch_orders_for_month(self, month: int, year: int) -> List[Order]:
        """
        Fetch all orders and their products for a given year-month.
        month = "07" (zero-padded), year = 2024.
        Returns list of Order ORM entities with products eagerly loaded.
        """
        date_start = f"{year:04d}-{month:02d}-01"
        if month == "12":
            next_month = "01"
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
        date_end = f"{next_year:04d}-{next_month:02d}-01"

        stmt = (
            select(Order)
            .where(Order.DATE >= date_start, Order.DATE < date_end)
            .order_by(Order.DATE.asc(), Order.ID.asc())
        )
        orders = self.session.execute(stmt).scalars().all()
        orders = [cast(Order, val) for val in orders]

        # Products are loaded via the relationship (lazy by default)
        # Accessing order.products triggers the lazy load.
        return orders

    # ── Query: fetch_order_by_id ────────────────────────────────────

    def fetch_order_by_id(self, order_id: str) -> Order | None:
        """Fetch a single order by ID with products eagerly loaded."""
        stmt = (
            select(Order)
            .where(Order.ID == order_id)
            .options(selectinload(Order.products))
        )
        result = self.session.execute(stmt).scalars().first()
        return cast(Order, result)

    # ── Query: search_products (paginated search) ───────────────────

    def search_products(
        self,
        page: int,
        supplier: Optional[str] = None,
        product: Optional[str] = None,
        month: Optional[str] = None,
    ) -> PageResponse[Product]:
        """
        Paginated product search with optional filters.
        page is 1-based.
        month format: "MM/yyyy" (e.g., "07/2024").

        Returns PageResponse with matching Product ORM entities.
        """
        where_clauses = [Product.ID.is_not(None)]

        # Filter by supplier (normalized LIKE)
        if supplier:
            normalized_supplier = normalize_text(supplier)
            where_clauses.append(Order.SUPPLIER_NORMALIZED.like(f"%{normalized_supplier}%"))

        # Filter by product name (normalized LIKE)
        if product:
            normalized_product = normalize_text(product)
            where_clauses.append(Product.NAME_NORMALIZED.like(f"%{normalized_product}%"))

        # Filter by month (MM/yyyy) - joins through ORDER table
        if month and len(month) == 7:
            try:
                m_str, y_str = month.split("/")
                m = int(m_str)
                y = int(y_str)
            except (ValueError, IndexError):
                raise ValueError(f"Formato de mes invalido: '{month}'")

            date_start = f"{y:04d}-{m:02d}-01"
            if m == 12:
                next_m = 1
                next_y = y + 1
            else:
                next_m = m + 1
                next_y = y
            date_end = f"{next_y:04d}-{next_m:02d}-01"

            subquery = (
                select(Order.ID)
                .where(Order.DATE >= date_start, Order.DATE < date_end)
                .scalar_subquery()
            )
            where_clauses.append(Product.ORDER_ID.in_(subquery))

        # Total count (for pagination)
        count_stmt = select(func.count()).join(Product.order).where(*where_clauses)
        total = self.session.scalar(count_stmt)
        total = int(total or 0)

        # Page count
        page_count = ceil(total / PAGE_SIZE)

        # Fetch page
        offset = (page - 1) * PAGE_SIZE
        query_stmt = (
            select(Product)
            .join(Product.order)
            .options(selectinload(Product.order))
            .where(*where_clauses)
            .order_by(Order.DATE.desc())
            .limit(PAGE_SIZE)
            .offset(offset)
        )
        products = self.session.execute(query_stmt).scalars().all()

        return PageResponse(
            items=list(products),
            page=page,
            page_count=page_count,
            total=total,
            page_size=PAGE_SIZE,
        )

    # ── Write: delete_orders ────────────────────────────────────────

    def delete_orders(self, order_ids: Sequence[str]) -> None:
        """Delete orders by their UUIDs. Called inside a transaction."""
        if not order_ids:
            return
        stmt = delete(Order).where(Order.ID.in_(order_ids))
        self.session.execute(stmt)

    # ── Write: insert_order ─────────────────────────────────────────

    def insert_order(self, order: OrderInput) -> None:
        """Insert a single order row. Timestamps are auto-generated by DB."""
        nfe_key_val = order.nfe_key if order.nfe_key else None
        now = datetime.now()
        order_entity = Order(
            ID=order.id,
            DATE=order.date,
            SUPPLIER=order.supplier,
            SUPPLIER_NORMALIZED=normalize_text(order.supplier),
            NFE_KEY=nfe_key_val,
            FREIGHT=order.freight,
            UNLOADING=order.unloading,
            CREATED_AT=now,
            UPDATED_AT=now,
        )
        self.session.add(order_entity)

    # ── Write: delete_order_products ────────────────────────────────

    def delete_order_products(self, order_ids: Sequence[str]) -> None:
        """Delete all products belonging to given order IDs."""
        if not order_ids:
            return
        stmt = delete(Product).where(Product.ORDER_ID.in_(order_ids))
        self.session.execute(stmt)

    # ── Write: insert_product ───────────────────────────────────────

    def insert_product(self, product: ProductInput) -> None:
        """Insert a single product row. Timestamps are auto-generated by DB."""
        now = datetime.now()
        product_entity = Product(
            ID=product.id,
            NAME=product.name,
            NAME_NORMALIZED=normalize_text(product.name),
            QUANTITY=product.quantity,
            PRICE=product.price,
            TOTAL_PRICE=product.total,
            ORDER_ID=product.order_id,
            ITEM_ORDINAL=product.item_ordinal,
            CREATED_AT=now,
            UPDATED_AT=now,
        )
        self.session.add(product_entity)
