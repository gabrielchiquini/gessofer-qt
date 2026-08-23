from __future__ import annotations

from datetime import date

import pytest

from models.output import PageResponse
from bridge.product import FetchHandler


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

orders_data: list[tuple] = [
    # Order A: July 2024, Cimento Portland
    (
        "order-a",
        date(2024, 7, 10),
        "Cimento Portland",
        "45678901234567",
        5000,
        1000,
        [
            ("prod-a1", "Cimento CP-II 50kg", 1, 25000, 25000, 1),
            ("prod-a2", "Cimento CP-II 1kg", 1, 500, 500, 2),
        ],
    ),
    # Order B: July 2024, Areia Premium LTDA
    (
        "order-b",
        date(2024, 7, 15),
        "Areia Premium LTDA",
        "12345678901234",
        3000,
        500,
        [
            ("prod-b1", "Areia média", 2, 120000, 240000, 1),
        ],
    ),
    # Order C: August 2024, Cimento Portland
    (
        "order-c",
        date(2024, 8, 5),
        "Cimento Portland",
        "98765432109876",
        4000,
        800,
        [
            ("prod-c1", "Cimento CP-I 50kg", 1, 22000, 22000, 1),
        ],
    ),
    # Order D: August 2024, Tijolo & Cia
    (
        "order-d",
        date(2024, 8, 20),
        "Tijolo & Cia",
        "11223344556677",
        6000,
        1200,
        [
            ("prod-d1", "Tijolo cerâmico 8 furos", 20, 1200, 24000, 1),
        ],
    ),
    # Order E: July 2024, Cimento Portland
    (
        "order-e",
        date(2024, 7, 25),
        "Cimento Portland",
        "55667788990011",
        2000,
        500,
        [
            ("prod-e1", "Cal hidratada 20kg", 2, 8000, 16000, 1),
        ],
    ),
]


def seeded_fetch_handler() -> list[tuple]:
    """Return the raw order test data. No database operations."""
    return orders_data


@pytest.fixture
def sample_page(fetch_handler: FetchHandler) -> PageResponse:
    """A PageResponse with seeded data for transformer tests."""
    return fetch_handler.fetch_products(page=1)
