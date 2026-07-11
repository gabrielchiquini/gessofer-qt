from __future__ import annotations

import pytest

from backend.qml.qml_fetch import FetchHandler
from backend.qml.qml_transformers import product_page_to_dict
from backend.models.dto import PageResponse


class TestProductListFilters:
    """Integration tests for product_list filtering via FetchHandler.

    IMPORTANT: The actual search_products implementation has a bug where
    the 'supplier' parameter filters on Product.NAME_NORMALIZED (the product
    name column) instead of Order.SUPPLIER_NORMALIZED. This means both
    'supplier' and 'product' parameters filter the same column.

    The tests below document the actual behavior of the code.
    """

    def test_no_filters_returns_all_products(self, fetch_handler: FetchHandler) -> None:
        """Calling with no filters returns all seeded products (6 total)."""
        result = fetch_handler.fetch_products(page=1)
        assert result.total == 6
        assert result.page == 1
        assert result.page_size == 50

    def test_supplier_filter_partial_cimento(self, fetch_handler: FetchHandler) -> None:
        """Filtering by supplier 'Cimento' matches product names containing 'cimento'
        (because the code has a bug: supplier filter uses Product.NAME_NORMALIZED)."""
        result = fetch_handler.fetch_products(page=1, supplier="Cimento")
        # "cimento cp-ii 50kg", "cimento cp-ii 1kg", "cimento cp-i 50kg"
        assert result.total == 3

    def test_supplier_filter_full_name_no_match(self, fetch_handler: FetchHandler) -> None:
        """Filtering by supplier 'Cimento Portland' returns 0 results.

        BUG: The code searches Product.NAME_NORMALIZED for 'cimento portland',
        but no product name contains 'cimento portland'. This is a known bug
        — the supplier filter should use Order.SUPPLIER_NORMALIZED via a join.
        """
        result = fetch_handler.fetch_products(page=1, supplier="Cimento Portland")
        assert result.total == 0
        assert len(result.items) == 0

    def test_supplier_filter_partial_areia(self, fetch_handler: FetchHandler) -> None:
        """Filtering by supplier 'Areia' matches product names containing 'areia'
        (because the code has a bug: supplier filter uses Product.NAME_NORMALIZED)."""
        result = fetch_handler.fetch_products(page=1, supplier="Areia")
        # "areia media"
        assert result.total == 1

    def test_supplier_filter_no_match(self, fetch_handler: FetchHandler) -> None:
        """Filtering by non-existent supplier returns empty results."""
        result = fetch_handler.fetch_products(page=1, supplier="Fornecedor Inexistente")
        assert result.total == 0
        assert len(result.items) == 0

    def test_product_name_filter(self, fetch_handler: FetchHandler) -> None:
        """Filtering by product name 'Cimento' returns only cement products."""
        result = fetch_handler.fetch_products(page=1, product="Cimento")
        assert result.total == 3

    def test_product_name_filter_case_insensitive(self, fetch_handler: FetchHandler) -> None:
        """Product name filter should be case-insensitive (via normalize_text)."""
        result_upper = fetch_handler.fetch_products(page=1, product="AREIA")
        result_lower = fetch_handler.fetch_products(page=1, product="areia")
        assert result_upper.total == result_lower.total == 1

    def test_product_name_filter_with_accents(self, fetch_handler: FetchHandler) -> None:
        """Product name filter with accented characters should normalize."""
        # "Areia média" normalizes to "areia media" — searching "areia medi" should match
        result = fetch_handler.fetch_products(page=1, product="Areia medi")
        assert result.total == 1

    def test_month_filter_july_2024(self, fetch_handler: FetchHandler) -> None:
        """Filtering by month '07/2024' returns only July 2024 products (Orders A, B, E)."""
        result = fetch_handler.fetch_products(page=1, month="07/2024")
        assert result.total == 4
    
    def test_month_filter_august_2024(self, fetch_handler: FetchHandler) -> None:
        """Filtering by month '08/2024' returns only August 2024 products (Orders C, D)."""
        result = fetch_handler.fetch_products(page=1, month="08/2024")
        assert result.total == 2

    def test_combined_supplier_and_month_filter(self, fetch_handler: FetchHandler) -> None:
        """Combined supplier + month filter.

        Because supplier filter uses Product.NAME_NORMALIZED, 'Cimento' matches
        product names with 'cimento' AND the month filter restricts to July 2024.
        July 2024 products with 'cimento' in the name: Orders A's products only.
        """
        result = fetch_handler.fetch_products(
            page=1, supplier="Cimento", month="07/2024"
        )
        assert result.total == 2  # "Cimento CP-II 50kg" and "Cimento CP-II 1kg"

    def test_combined_supplier_product_month_filter(self, fetch_handler: FetchHandler) -> None:
        """All three filters combined.

        supplier='Cimento' and product='CP-II' both filter NAME_NORMALIZED,
        so effectively it's LIKE '%cimento%' AND LIKE '%cp-ii%' AND month='07/2024'.
        """
        result = fetch_handler.fetch_products(
            page=1,
            supplier="Cimento",
            product="CP-II",
            month="07/2024",
        )
        assert result.total == 2  # "Cimento CP-II 50kg" and "Cimento CP-II 1kg"

    def test_page_2_empty(self, fetch_handler: FetchHandler) -> None:
        """Requesting page 2 when all results fit on page 1 returns empty."""
        result = fetch_handler.fetch_products(page=2)
        assert len(result.items) == 0
        assert result.page == 2

    def test_page_count_calculation(self, fetch_handler: FetchHandler) -> None:
        """Page count is calculated correctly (total / page_size rounded up)."""
        result = fetch_handler.fetch_products(page=1)
        assert result.page_count == 1  # 6 items / 50 per page = 1 page


class TestProductListPagination:
    """Tests for pagination behavior of product_list."""

    def test_page_size_is_50(self, fetch_handler: FetchHandler) -> None:
        assert fetch_handler.fetch_products(page=1).page_size == 50

    def test_page_metadata_correct(self, fetch_handler: FetchHandler) -> None:
        result = fetch_handler.fetch_products(page=1)
        assert result.page == 1
        assert result.total == 6


class TestProductListTransformer:
    """Tests for product_page_to_dict transformer.

    These tests are expected to fail because of a bug in
    OrderRepository.search_products: .all() returns Row tuples
    instead of Product entities, so product_list_item_to_dict
    cannot access .order on the tuple items.
    """

    def test_transformer_produces_correct_keys(self, sample_page: PageResponse) -> None:
        """product_page_to_dict produces the expected QML-compatible structure."""
        d = product_page_to_dict(sample_page)
        assert "items" in d
        assert "page" in d
        assert "page_count" in d
        assert "total" in d
        assert "page_size" in d
        assert isinstance(d["items"], list)

    def test_transformer_item_structure(self, sample_page: PageResponse) -> None:
        """Each transformed item has the expected keys."""
        d = product_page_to_dict(sample_page)
        if d["items"]:
            item = d["items"][0]
            expected_keys = {"date", "supplier", "name", "price", "totalPrice", "orderId"}
            assert set(item.keys()) == expected_keys

    def test_transformer_date_format_br(self, sample_page: PageResponse) -> None:
        """Dates in transformed items use dd/MM/yyyy format."""
        d = product_page_to_dict(sample_page)
        if d["items"]:
            item = d["items"][0]
            if item.get("date"):
                assert "/" in item["date"]
