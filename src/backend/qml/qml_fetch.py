from __future__ import annotations

from typing import Callable

from sqlalchemy.orm import Session

from backend.entities.orm import Expense, Order, Product
from backend.models.dto import PageResponse
from backend.repositories.expense_repository import ExpenseRepository
from backend.repositories.order_repository import OrderRepository
from backend.utils.date import parse_month_for_expenses, parse_month_for_orders


class FetchHandler:
    """Handles all data-fetch operations for the QML layer."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def fetch_orders_for_month(self, month: str) -> list[Order]:
        """Fetch ORM Order entities with products for a given MM/yyyy month."""
        m, y = parse_month_for_orders(month)
        with self._session_factory() as session:
            return OrderRepository(session).fetch_orders_for_month(month=m, year=y)

    def fetch_products(
        self,
        page: int,
        supplier: str | None = None,
        product: str | None = None,
        month: str | None = None,
    ) -> PageResponse[Product]:
        """Fetch paginated product search results."""
        with self._session_factory() as session:
            return OrderRepository(session).search_products(
                page=page, supplier=supplier, product=product, month=month,
            )

    def fetch_expenses_for_month(self, month: str) -> list[Expense]:
        """Fetch ORM Expense entities for a given YYYY-MM month."""
        validated = parse_month_for_expenses(month)
        with self._session_factory() as session:
            return ExpenseRepository(session).fetch_expenses_for_month(month=validated)
