from __future__ import annotations

from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from backend.services.order_service import OrderService
from backend.utils.currency import cents_to_view
from backend.utils.date import datetime_to_br_date
from di.injector_module import get_injector
from frontend.views.product_list import ProductListView
from tests.fixtures.seed_data import ORDERS_DATA


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
        order_service: OrderService = injector.get(OrderService)

        widget = ProductListView(
            parent=None,
            order_service=order_service,
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
        assert widget._model.item(0, 1).text() == ORDERS_DATA[2].supplier
        assert widget._model.item(0, 2).text() == ORDERS_DATA[2].products[0].name
        assert widget._model.item(3, 2).text() == ORDERS_DATA[0].products[1].name


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
        assert widget._model.item(0, 1).text() == ORDERS_DATA[1].supplier
        assert widget._model.item(0, 2).text() == ORDERS_DATA[1].products[0].name


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
        assert widget._model.item(0, 0).text().endswith("/07/2024")
        assert widget._model.item(0, 0).text() == datetime_to_br_date(ORDERS_DATA[4].date)
        assert widget._model.item(3, 0).text() == datetime_to_br_date(ORDERS_DATA[0].date)


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

        # Row 0: Order D (2024-08-20) → Tijolo cerâmico 8 furos (Tijolo & Cia)
        assert widget._model.item(0, 0).text() == datetime_to_br_date(ORDERS_DATA[3].date)
        assert widget._model.item(0, 1).text() == ORDERS_DATA[3].supplier
        assert widget._model.item(0, 2).text() == ORDERS_DATA[3].products[0].name
        assert widget._model.item(0, 3).text() == cents_to_view(ORDERS_DATA[3].products[0].price)
        assert widget._model.item(0, 4).text() == cents_to_view(ORDERS_DATA[3].products[0].price_with_freight)

        # Row 1: Order C (2024-08-05) → Cimento CP-I 50kg (Cimento Portland)
        assert widget._model.item(1, 0).text() == datetime_to_br_date(ORDERS_DATA[2].date)
        assert widget._model.item(1, 1).text() == ORDERS_DATA[2].supplier
        assert widget._model.item(1, 2).text() == ORDERS_DATA[2].products[0].name
        assert widget._model.item(1, 3).text() == cents_to_view(ORDERS_DATA[2].products[0].price)
        assert widget._model.item(1, 4).text() == cents_to_view(ORDERS_DATA[2].products[0].price_with_freight)

        # Row 2: Order E (2024-07-25) → Cal hidratada 20kg (Cimento Portland)
        assert widget._model.item(2, 0).text() == datetime_to_br_date(ORDERS_DATA[4].date)
        assert widget._model.item(2, 1).text() == ORDERS_DATA[4].supplier
        assert widget._model.item(2, 2).text() == ORDERS_DATA[4].products[0].name
        assert widget._model.item(2, 3).text() == cents_to_view(ORDERS_DATA[4].products[0].price)
        assert widget._model.item(2, 4).text() == cents_to_view(ORDERS_DATA[4].products[0].price_with_freight)

        # Row 3: Order B (2024-07-15) → Areia média (Areia Premium LTDA)
        assert widget._model.item(3, 0).text() == datetime_to_br_date(ORDERS_DATA[1].date)
        assert widget._model.item(3, 1).text() == ORDERS_DATA[1].supplier
        assert widget._model.item(3, 2).text() == ORDERS_DATA[1].products[0].name
        assert widget._model.item(3, 3).text() == cents_to_view(ORDERS_DATA[1].products[0].price)
        assert widget._model.item(3, 4).text() == cents_to_view(ORDERS_DATA[1].products[0].price_with_freight)

        # Row 4: Order A product 1 (2024-07-10) → Cimento CP-II 50kg (Cimento Portland)
        assert widget._model.item(4, 0).text() == datetime_to_br_date(ORDERS_DATA[0].date)
        assert widget._model.item(4, 1).text() == ORDERS_DATA[0].supplier
        assert widget._model.item(4, 2).text() == ORDERS_DATA[0].products[0].name
        assert widget._model.item(4, 3).text() == cents_to_view(ORDERS_DATA[0].products[0].price)
        assert widget._model.item(4, 4).text() == cents_to_view(ORDERS_DATA[0].products[0].price_with_freight)

        # Row 5: Order A product 2 (2024-07-10) → Cimento CP-II 1kg (Cimento Portland)
        assert widget._model.item(5, 0).text() == datetime_to_br_date(ORDERS_DATA[0].date)
        assert widget._model.item(5, 1).text() == ORDERS_DATA[0].supplier
        assert widget._model.item(5, 2).text() == ORDERS_DATA[0].products[1].name
        assert widget._model.item(5, 3).text() == cents_to_view(ORDERS_DATA[0].products[1].price)
        assert widget._model.item(5, 4).text() == cents_to_view(ORDERS_DATA[0].products[1].price_with_freight)


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
