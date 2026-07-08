from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.entities.orm import Order, Product
from backend.models.dto import PageResponse
from backend.repositories.order_repository import OrderRepository
from backend.utils.date import parse_month_for_orders


def orders_for_month(month: str) -> List[Order]:
    """
    Fetch all orders and their products for a given month.

    Args:
        month: Month string in 'MM/yyyy' format (e.g., '07/2024').

    Returns:
        List of Order ORM entities with products eagerly accessible.

    Raises:
        BackendError: If the month format is invalid or a database error occurs.
    """
    try:
        m, y = parse_month_for_orders(month)
    except ValueError as exc:
        raise ValueError(f"Formato de mês inválido: '{month}'. Esperado 'MM/yyyy'.") from exc

    engine = get_engine()
    with Session(engine) as session:
        repo = OrderRepository(session)
        return repo.fetch_orders_for_month(month=m, year=y)


def product_list(
    page: int = 1,
    supplier: Optional[str] = None,
    product: Optional[str] = None,
    month: Optional[str] = None,
) -> PageResponse[Product]:
    """
    Paginated product listing with optional filters.

    Args:
        page: Page number (1-based). Defaults to 1.
        supplier: Optional supplier name filter (fuzzy match).
        product: Optional product name filter (fuzzy match).
        month: Optional month filter in 'MM/yyyy' format.

    Returns:
        PageResponse with matching Product ORM entities.

    Raises:
        BackendError: If a database error occurs.
    """
    engine = get_engine()
    with Session(engine) as session:
        repo = OrderRepository(session)
        return repo.search_products(
            page=page,
            supplier=supplier,
            product=product,
            month=month,
        )
