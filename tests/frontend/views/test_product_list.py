from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from bridge.product import ProductBridge
from di.injector_module import get_injector
from frontend.views.product_list import ProductListView


# ── TC-01: Initial Load ───────────────────────────────────────────


class TestProductListInitialLoad:
    """TC-01: Widget initializes with all 6 seeded products and single-page pagination."""

    def test_initial_load(
            self,
            temp_engine: Engine,
            qtbot: QtBot,
        ) -> None:
        """Show the widget and verify initial state with seeded data."""
        injector = get_injector()
        product_bridge: ProductBridge = injector.get(ProductBridge)

        widget = ProductListView(
            parent=None,
            product_bridge=product_bridge,
        )
        qtbot.addWidget(widget)
        widget.show()

        assert widget.scroll.isVisible() is True
        assert widget._model.rowCount() == 6
        assert widget.page_label.text() == "Página 1 de 1"
        assert widget.btn_prev.isEnabled() is False
        assert widget.btn_next.isEnabled() is False
        assert widget.filter_supplier.text() == ""
        assert widget.filter_product.text() == ""
        assert widget.filter_month.text() == "/"


# ── TC-02: Supplier Filter ────────────────────────────────────────


class TestProductListSupplierFilter:
    """TC-02: Filtering by supplier name narrows results correctly."""

    def test_supplier_filter(
            self,
            product_list_widget: ProductListView,
            qtbot: QtBot,
        ) -> None:
        """Filter by supplier 'Cimento' and verify 4 matching products."""
        widget = product_list_widget

        widget.filter_supplier.setText("Cimento")
        widget.btn_search.click()

        assert widget._model.rowCount() == 4
        assert widget.page_label.text() == "Página 1 de 1"
        assert widget._model.item(0, 1).text() == "Cimento Portland"
        assert widget._model.item(0, 2).text() == "Cimento CP-I 50kg"
        assert widget._model.item(3, 2).text() == "Cimento CP-II 1kg"


# ── TC-03: Product Name Filter ────────────────────────────────────


class TestProductListProductNameFilter:
    """TC-03: Filtering by product name narrows results correctly."""

    def test_product_name_filter(
            self,
            product_list_widget: ProductListView,
            qtbot: QtBot,
        ) -> None:
        """Filter by product 'Areia' and verify 1 matching product."""
        widget = product_list_widget

        widget.filter_product.setText("Areia")
        widget.btn_search.click()

        assert widget._model.rowCount() == 1
        assert widget._model.item(0, 1).text() == "Areia Premium LTDA"
        assert widget._model.item(0, 2).text() == "Areia média"


# ── TC-04: Month Filter ───────────────────────────────────────────


class TestProductListMonthFilter:
    """TC-04: Filtering by month narrows results correctly."""

    def test_month_filter(
            self,
            product_list_widget: ProductListView,
            qtbot: QtBot,
        ) -> None:
        """Filter by month '07/2024' and verify 4 matching products."""
        widget = product_list_widget

        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        assert widget._model.rowCount() == 4
        assert widget._model.item(0, 0).text() == "25/07/2024"
        assert widget._model.item(3, 0).text() == "10/07/2024"


# ── TC-05: Combined Filters ───────────────────────────────────────


class TestProductListCombinedFilters:
    """TC-05: Multiple filters combine with AND logic."""

    def test_combined_filters(
            self,
            product_list_widget: ProductListView,
            qtbot: QtBot,
        ) -> None:
        """Filter by supplier 'Cimento' and month '07/2024' and verify 3 results."""
        widget = product_list_widget

        widget.filter_supplier.setText("Cimento")
        widget.filter_month.setText("07/2024")
        widget.btn_search.click()

        assert widget._model.rowCount() == 3
        for row in range(widget._model.rowCount()):
            assert widget._model.item(row, 1).text() == "Cimento Portland"
            assert widget._model.item(row, 0).text().endswith("/07/2024")


# ── TC-06: Display Data Correctness ───────────────────────────────


class TestProductListDisplayCorrectness:
    """TC-06: All cells display correct data in correct order."""

    def test_display_correctness(
            self,
            product_list_widget: ProductListView,
        ) -> None:
        """Verify every cell in the table matches expected seeded data."""
        widget = product_list_widget

        widget.btn_search.click()

        assert widget._model.rowCount() == 6

        # Row 0: 20/08/2024 | Tijolo & Cia | Tijolo cerâmico 8 furos | 12,00 | 240,00
        assert widget._model.item(0, 0).text() == "20/08/2024"
        assert widget._model.item(0, 1).text() == "Tijolo & Cia"
        assert widget._model.item(0, 2).text() == "Tijolo cerâmico 8 furos"
        assert widget._model.item(0, 3).text() == "12,00"
        assert widget._model.item(0, 4).text() == "240,00"

        # Row 1: 05/08/2024 | Cimento Portland | Cimento CP-I 50kg | 220,00 | 220,00
        assert widget._model.item(1, 0).text() == "05/08/2024"
        assert widget._model.item(1, 1).text() == "Cimento Portland"
        assert widget._model.item(1, 2).text() == "Cimento CP-I 50kg"
        assert widget._model.item(1, 3).text() == "220,00"
        assert widget._model.item(1, 4).text() == "220,00"

        # Row 2: 25/07/2024 | Cimento Portland | Cal hidratada 20kg | 80,00 | 160,00
        assert widget._model.item(2, 0).text() == "25/07/2024"
        assert widget._model.item(2, 1).text() == "Cimento Portland"
        assert widget._model.item(2, 2).text() == "Cal hidratada 20kg"
        assert widget._model.item(2, 3).text() == "80,00"
        assert widget._model.item(2, 4).text() == "160,00"

        # Row 3: 15/07/2024 | Areia Premium LTDA | Areia média | 1200,00 | 2400,00
        assert widget._model.item(3, 0).text() == "15/07/2024"
        assert widget._model.item(3, 1).text() == "Areia Premium LTDA"
        assert widget._model.item(3, 2).text() == "Areia média"
        assert widget._model.item(3, 3).text() == "1200,00"
        assert widget._model.item(3, 4).text() == "2400,00"

        # Row 4: 10/07/2024 | Cimento Portland | Cimento CP-II 50kg | 250,00 | 250,00
        assert widget._model.item(4, 0).text() == "10/07/2024"
        assert widget._model.item(4, 1).text() == "Cimento Portland"
        assert widget._model.item(4, 2).text() == "Cimento CP-II 50kg"
        assert widget._model.item(4, 3).text() == "250,00"
        assert widget._model.item(4, 4).text() == "250,00"

        # Row 5: 10/07/2024 | Cimento Portland | Cimento CP-II 1kg | 5,00 | 5,00
        assert widget._model.item(5, 0).text() == "10/07/2024"
        assert widget._model.item(5, 1).text() == "Cimento Portland"
        assert widget._model.item(5, 2).text() == "Cimento CP-II 1kg"
        assert widget._model.item(5, 3).text() == "5,00"
        assert widget._model.item(5, 4).text() == "5,00"


# ── TC-07: Empty State ────────────────────────────────────────────


class TestProductListEmptyState:
    """TC-07: Empty state when no products match the filter."""

    def test_empty_state(
            self,
            product_list_widget: ProductListView,
        ) -> None:
        """Filter by a month with no data and verify empty state."""
        widget = product_list_widget

        widget.filter_month.setText("01/2023")
        widget.btn_search.click()

        assert widget._model.rowCount() == 0
        assert widget.page_label.text() == "Página 1 de 0"
        assert widget.btn_prev.isEnabled() is False
        assert widget.btn_next.isEnabled() is False
        assert widget.scroll.isVisible() is True


# ── TC-08: Pagination UI ──────────────────────────────────────────


class TestProductListPagination:
    """TC-08: Pagination handles boundary conditions correctly."""

    def test_pagination_boundaries(
            self,
            product_list_widget: ProductListView,
            qtbot: QtBot,
        ) -> None:
        """Verify single-page pagination boundary behavior."""
        widget = product_list_widget

        assert widget._page_count == 1
        assert widget._current_page == 1
        assert widget.page_label.text() == "Página 1 de 1"

        widget.go_previous()
        assert widget._current_page == 1

        widget.go_next()
        assert widget._current_page == 1

        assert widget.btn_prev.isEnabled() is False
        assert widget.btn_next.isEnabled() is False


# ── TC-09: Clear Filters ──────────────────────────────────────────


class TestProductListClearFilters:
    """TC-09: clear_filters() resets all state and reloads data."""

    def test_clear_filters(
            self,
            product_list_widget: ProductListView,
            qtbot: QtBot,
        ) -> None:
        """Apply a filter, then clear and verify all data is restored."""
        widget = product_list_widget

        # Apply filter
        widget.filter_supplier.setText("Cimento")
        widget.btn_search.click()
        assert widget._model.rowCount() == 4

        # Clear filters
        widget.clear_filters()

        # Verify filters are empty
        assert widget.filter_supplier.text() == ""
        assert widget.filter_product.text() == ""
        assert widget.filter_month.text() == "/"

        # Verify all data restored
        assert widget._model.rowCount() == 6
        assert widget.page_label.text() == "Página 1 de 1"


# ── TC-10: Enter Key Triggers Search ──────────────────────────────


class TestProductListEnterKeySearch:
    """TC-10: Pressing Enter in a filter field triggers search."""

    def test_enter_key_triggers_search(
            self,
            product_list_widget: ProductListView,
            qtbot: QtBot,
        ) -> None:
        """Type in filter_product and emit returnPressed to trigger search."""
        widget = product_list_widget

        widget.filter_product.setText("Areia")
        widget.filter_product.returnPressed.emit()

        assert widget._model.rowCount() == 1
        assert widget._model.item(0, 2).text() == "Areia média"
