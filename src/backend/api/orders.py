from __future__ import annotations

from typing import Callable, List, Optional

from backend.injector_module import call_with_injection
from sqlalchemy.orm import Session

from backend.entities.orm import Order, Product
from backend.models.dto import PageResponse
from backend.repositories.order_repository import OrderRepository
from backend.utils.date import parse_month_for_orders


def orders_for_month(
    month: str,
    session_factory: Callable[[], Session],
) -> List[Order]:
    """
    Fetch all orders and their products for a given month.

    Args:
        month: Month string in 'MM/yyyy' format (e.g., '07/2024').
        session_factory: Injected factory that creates new Sessions.

    Returns:
        List of Order ORM entities with products eagerly accessible.

    Raises:
        ValueError: If the month format is invalid.
        BackendError: If a database error occurs.
    """
    try:
        m, y = parse_month_for_orders(month)
    except ValueError as exc:
        raise ValueError(f"Formato de mês inválido: '{month}'. Esperado 'MM/yyyy'.") from exc

    with session_factory() as session:
        repo = OrderRepository(session)
        return repo.fetch_orders_for_month(month=m, year=y)


def product_list(
    page: int = 1,
    supplier: Optional[str] = None,
    product: Optional[str] = None,
    month: Optional[str] = None,
    session_factory: Callable[[], Session] = None,  # type: ignore[assignment]
) -> PageResponse[Product]:
    """
    Paginated product listing with optional filters.

    Args:
        page: Page number (1-based). Defaults to 1.
        supplier: Optional supplier name filter (fuzzy match).
        product: Optional product name filter (fuzzy match).
        month: Optional month filter in 'MM/yyyy' format.
        session_factory: Injected factory that creates new Sessions.

    Returns:
        PageResponse with matching Product ORM entities.

    Raises:
        BackendError: If a database error occurs.
    """
    with session_factory() as session:
        repo = OrderRepository(session)
        return repo.search_products(
            page=page,
            supplier=supplier,
            product=product,
            month=month,
        )


# Wrap functions with injection — BackendManager calls these wrapped versions
def _orders_for_month_injected(month: str) -> List[Order]:
    """Injected wrapper for orders_for_month."""
    return call_with_injection(orders_for_month, month)


def _product_list_injected(
    page: int = 1,
    supplier: Optional[str] = None,
    product: Optional[str] = None,
    month: Optional[str] = None,
) -> PageResponse[Product]:
    """Injected wrapper for product_list."""
    return call_with_injection(
        product_list,
        page,
        supplier=supplier,
        product=product,
        month=month,
    )


def get_orders_for_month_injected() -> Callable[[str], List[Order]]:
    """Return the injected version of orders_for_month for BackendManager."""
    return _orders_for_month_injected


def get_product_list_injected() -> Callable[..., PageResponse[Product]]:
    """Return the injected version of product_list for BackendManager."""
    return _product_list_injected
