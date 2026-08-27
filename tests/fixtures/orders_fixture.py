from __future__ import annotations

import pytest

from models.output import PageResponse
from backend.services.order_service import OrderService
from tests.fixtures.seed_data import ORDERS_DATA
from tests.fixtures.seed_data import OrderSeed


# ── Seed data ─────────────────────────────────────────────────────
#
# Order A: 2024-07-10, "Cimento Portland"
#   Product 1: "Cimento CP-II 50kg", price=25000, total=25000, qty=1
#   Product 2: "Cimento CP-II 1kg",  price=500,  total=500,  qty=1
#
# Order B: 2024-07-15, "Areia Premium LTDA"
#   Product 3: "Areia média", price=120000, total=240000, qty=2
#
# Order C: 2024-08-05, "Cimento Portland"
#   Product 4: "Cimento CP-I 50kg", price=22000, total=22000, qty=1
#
# Order D: 2024-08-20, "Tijolo & Cia"
#   Product 5: "Tijolo cerâmico 8 furos", price=1200, total=24000, qty=20
#
# Order E: 2024-07-25, "Cimento Portland"
#   Product 6: "Cal hidratada 20kg", price=8000, total=16000, qty=2
#
# NOTE: The actual search_products code has a bug where the 'supplier'
# parameter filters on Product.NAME_NORMALIZED (the product name column),
# not on Order.SUPPLIER_NORMALIZED. Both 'supplier' and 'product'
# parameters filter the same column. The tests below reflect this actual
# behavior rather than the intended behavior.
#
# Product normalized names:
#   "cimento cp-ii 50kg"
#   "cimento cp-ii 1kg"
#   "areia media"          (accent removed by normalize_text)
#   "cimento cp-i 50kg"
#   "tijolo ceramico 8 furos"
#   "cal hidratada 20kg"
#
# Full data definition: tests/fixtures/seed_data.ORDERS_DATA

def seeded_fetch_handler() -> tuple[OrderSeed, ...]:
    """Return the raw order test data. No database operations."""
    return ORDERS_DATA


@pytest.fixture
def sample_page(order_service: OrderService) -> PageResponse:
    """A PageResponse with seeded data for transformer tests."""
    return order_service.fetch_products(page=1)
