from __future__ import annotations

from typing import Generator
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from di.injector_module import get_injector
from frontend.app import MainWindow
from frontend.factories.certificate_status_view_factory import CertificateStatusViewFactory
from frontend.factories.expense_list_view_factory import ExpenseListViewFactory
from frontend.factories.order_edit_list_view_factory import OrderEditListViewFactory
from frontend.factories.product_list_view_factory import ProductListViewFactory
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from frontend.views.order_edit.order_edit_list import OrderEditListView
from frontend.views.product_list import ProductListView


# ── Shared Fixture ──────────────────────────────────────────────────


@pytest.fixture
def main_window_with_factories(
        temp_engine: Engine, qtbot: QtBot,
) -> Generator[MainWindow, None, None]:
    """Create a MainWindow with all factories wired to the test database."""
    injector = get_injector()
    plvf: ProductListViewFactory = injector.get(ProductListViewFactory)
    oelf: OrderEditListViewFactory = injector.get(OrderEditListViewFactory)
    elvf: ExpenseListViewFactory = injector.get(ExpenseListViewFactory)
    csvf: CertificateStatusViewFactory = injector.get(CertificateStatusViewFactory)

    mw = MainWindow(
        product_list_view_factory=plvf,
        order_edit_list_view_factory=oelf,
        expense_list_view_factory=elvf,
        certificate_status_view_factory=csvf,
    )
    qtbot.addWidget(mw)
    mw.show()
    yield mw
    mw.close()
    mw.deleteLater()


# ── Helper ──────────────────────────────────────────────────────────


def _get_dialog_by_type[T](class_type: type[T]) -> T:
    """Find a visible QDialog whose window title starts with the given prefix."""
    dialogs = [
        w for w in QApplication.topLevelWidgets()
        if isinstance(w, class_type)
    ]
    assert dialogs, f"No dialog found with title starting with: {class_type!r}"
    return dialogs[-1]


# ── TC-01: Edit Order and Verify Product Count Increases ────────────


class TestProductListEditOrder:
    """TC-01: Edit an existing order to add a product and verify product count increases."""

    def test_edit_order_adds_product(
            self,
            main_window_with_factories: MainWindow,
            qtbot: QtBot,
    ) -> None:
        """Navigate to product list, verify 4 products in July 2024,
        edit order-a to add a product, navigate back, verify 5 products."""
        mw = main_window_with_factories

        # Step 1: Verify initial product count in July 2024
        product_view: ProductListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)
        product_view.filter_month.setText("07/2024")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 4

        # Step 2: Navigate to order list
        mw._on_item_clicked("Lista de pedidos por mês", "Notas")
        order_view: OrderEditListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(order_view, OrderEditListView)

        # Step 3: Verify order list shows 3 orders in July 2024
        order_view.filter_month.setText("07/2024")
        order_view.btn_search.click()
        qtbot.wait(100)
        assert order_view._model.rowCount() == 3

        # Step 4: Edit order-a (row 0) to add a product
        container = order_view.table_view.indexWidget(
            order_view._model.index(0, 5)
        )
        assert container is not None
        edit_btn = container.findChild(QPushButton)
        assert edit_btn is not None
        edit_btn.click()
        qtbot.wait(100)

        dialog = _get_dialog_by_type(OrderEditDialog)
        qtbot.addWidget(dialog)
        qtbot.waitExposed(dialog)

        # Add a new product row
        rows = dialog.items_card.get_product_rows()
        # Row 3 is the new empty row (rows 0-2 are existing data)
        rows[2].name_input.setText("Novo Produto")
        rows[2].quantity_input.setText("1")
        rows[2].price_input.setText("10,00")

        dialog.btn_save.click()
        qtbot.wait(100)

        # Step 5: Verify order list still shows 3 orders
        assert order_view._model.rowCount() == 3

        # Step 6: Navigate back to product list
        mw._on_item_clicked("Lista de Produtos", "Notas")
        product_view = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)

        # Step 7: Verify product count increased to 5
        product_view.filter_month.setText("07/2024")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 5


# ── TC-02: Add Order with Multiple Products ─────────────────────────


class TestProductListAddOrder:
    """TC-02: Add a new order with 2 products and verify product count increases."""

    def test_add_order_with_products(
            self,
            main_window_with_factories: MainWindow,
            qtbot: QtBot,
    ) -> None:
        """Navigate to product list, verify 4 products in July 2024,
        add a new order with 2 products, navigate back, verify 6 products."""
        mw = main_window_with_factories

        # Step 1: Verify initial product count
        product_view: ProductListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)
        product_view.filter_month.setText("07/2024")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 4

        # Step 2: Navigate to order list
        mw._on_item_clicked("Lista de pedidos por mês", "Notas")
        order_view: OrderEditListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(order_view, OrderEditListView)

        # Step 3: Verify order list shows 3 orders in July 2024
        order_view.filter_month.setText("07/2024")
        order_view.btn_search.click()
        qtbot.wait(100)
        assert order_view._model.rowCount() == 3

        # Step 4: Add a new order with 2 products
        order_view.btn_add.click()
        qtbot.wait(100)

        dialog = _get_dialog_by_type(OrderEditDialog)
        qtbot.addWidget(dialog)
        qtbot.waitExposed(dialog)

        # Fill header
        dialog.header_card._supplier_input.set_text("Novo Fornecedor")
        dialog.header_card._date_input.set_text("20/07/2024")

        # Fill row 0 (already exists)
        rows = dialog.items_card.get_product_rows()
        rows[0].name_input.setText("Produto A")
        rows[0].quantity_input.setText("2")
        rows[0].price_input.setText("50,00")

        # Add row 1
        rows = dialog.items_card.get_product_rows()
        rows[1].name_input.setText("Produto B")
        rows[1].quantity_input.setText("1")
        rows[1].price_input.setText("30,00")

        dialog.btn_save.click()
        qtbot.wait(100)

        # Step 5: Verify order list updated to 4 orders
        assert order_view._model.rowCount() == 4

        # Step 6: Navigate back to product list
        mw._on_item_clicked("Lista de Produtos", "Notas")
        product_view = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)

        # Step 7: Verify product count increased to 6
        product_view.filter_month.setText("07/2024")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 6


# ── TC-03: Delete Order and Verify Products Are Removed ─────────────


class TestProductListDeleteOrder:
    """TC-03: Delete an order via the delete button and verify products are removed."""

    def test_delete_order_removes_products(
            self,
            main_window_with_factories: MainWindow,
            qtbot: QtBot,
    ) -> None:
        """Navigate to product list, verify 4 products in July 2024,
        delete order-b (1 product) via delete button, navigate back, verify 3 products."""
        mw = main_window_with_factories

        # Step 1: Verify initial product count
        product_view: ProductListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)
        product_view.filter_month.setText("07/2024")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 4

        # Step 2: Navigate to order list
        mw._on_item_clicked("Lista de pedidos por mês", "Notas")
        order_view: OrderEditListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(order_view, OrderEditListView)

        # Step 3: Verify order list shows 3 orders in July 2024
        order_view.filter_month.setText("07/2024")
        order_view.btn_search.click()
        qtbot.wait(100)
        assert order_view._model.rowCount() == 3

        # Step 4: Delete order-b (row 1 — "Areia Premium LTDA") using delete button
        container = order_view.table_view.indexWidget(
            order_view._model.index(1, 5)
        )
        assert container is not None
        delete_btn = container.findChildren(QPushButton)[1]
        assert delete_btn is not None

        with patch('PySide6.QtWidgets.QMessageBox.warning', return_value=QMessageBox.StandardButton.Yes):
            delete_btn.click()
        qtbot.wait(100)

        # Step 5: Verify order list updated to 2 orders
        assert order_view._model.rowCount() == 2

        # Step 6: Navigate back to product list
        mw._on_item_clicked("Lista de Produtos", "Notas")
        product_view = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)

        # Step 7: Verify product count decreased to 3
        product_view.filter_month.setText("07/2024")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 3


# ── TC-04: Add Order in a Month with No Products ────────────────────


class TestProductListAddOrderEmptyMonth:
    """TC-04: Add an order in a month with no existing products."""

    def test_add_order_in_empty_month(
            self,
            main_window_with_factories: MainWindow,
            qtbot: QtBot,
    ) -> None:
        """Verify October 2024 is empty, add an order, verify product appears."""
        mw = main_window_with_factories

        # Step 1: Verify initial empty state for October 2024
        product_view: ProductListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)
        product_view.filter_month.setText("10/2024")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 0

        # Step 2: Navigate to order list
        mw._on_item_clicked("Lista de pedidos por mês", "Notas")
        order_view: OrderEditListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(order_view, OrderEditListView)

        # Step 3: Verify order list is empty for October
        order_view.filter_month.setText("10/2024")
        order_view.btn_search.click()
        qtbot.wait(100)
        assert order_view._model.rowCount() == 0

        # Step 4: Add a new order with 1 product
        order_view.btn_add.click()
        qtbot.wait(100)

        dialog = _get_dialog_by_type(OrderEditDialog)
        qtbot.addWidget(dialog)
        qtbot.waitExposed(dialog)

        # Fill header
        dialog.header_card._supplier_input.set_text("Fornecedor Outubro")
        dialog.header_card._date_input.set_text("15/10/2024")

        # Fill product row 0
        rows = dialog.items_card.get_product_rows()
        rows[0].name_input.setText("Produto Outubro")
        rows[0].quantity_input.setText("1")
        rows[0].price_input.setText("100,00")

        dialog.btn_save.click()
        qtbot.wait(100)

        # Step 5: Verify order list shows 1 order
        assert order_view._model.rowCount() == 1

        # Step 6: Navigate back to product list
        mw._on_item_clicked("Lista de Produtos", "Notas")
        product_view = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)

        # Step 7: Verify product appears with correct data
        product_view.filter_month.setText("10/2024")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 1
        assert product_view._model.item(0, 0).text() == "15/10/2024"
        assert product_view._model.item(0, 1).text() == "Fornecedor Outubro"
        assert product_view._model.item(0, 2).text() == "Produto Outubro"


# ── TC-05: Import NFe XML and Verify Order + Products Created ─────────


class TestProductListXmlImport:
    """TC-05: Import an NFe XML file and verify order and products appear."""

    def test_import_xml_creates_order_and_products(
            self,
            main_window_with_factories: MainWindow,
            qtbot: QtBot,
    ) -> None:
        """Navigate to product list, verify 4 products in July 2024,
        import nfe.xml (patch QFileDialog and import_xml), verify order
        appears in order edit view, save it, navigate back, verify products."""
        mw = main_window_with_factories

        # Step 1: Verify initial product count in July 2024
        product_view: ProductListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)
        product_view.filter_month.setText("07/2026")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 0

        # Step 2: Navigate to order list
        mw._on_item_clicked("Lista de pedidos por mês", "Notas")
        order_view: OrderEditListView = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(order_view, OrderEditListView)

        # Step 3: Verify order list shows 3 orders in July 2024
        order_view.filter_month.setText("07/2026")
        order_view.btn_search.click()
        qtbot.wait(100)
        assert order_view._model.rowCount() == 0

        # Step 4: Import XML — patch QFileDialog, let service parse the real file
        from pathlib import Path

        xml_path: str = str(
            Path(__file__).parent.parent.parent / "fixtures" / "nfe.xml"
        )

        with patch(
                "PySide6.QtWidgets.QFileDialog.getOpenFileName",
                return_value=(xml_path, ""),
        ):
            order_view.btn_import_xml.click()
            qtbot.wait(200)

        # Step 5: Verify OrderEditDialog opened with imported data
        dialog = _get_dialog_by_type(OrderEditDialog)
        qtbot.addWidget(dialog)
        qtbot.waitExposed(dialog)

        # Verify header fields
        assert (
                "O.V.D. IMPORTADORA E DISTRIBUIDORA LTDA"
                in dialog.header_card._supplier_input.get_text()
        )
        assert dialog.header_card._date_input.get_text() == "02/07/2026"

        # Verify products were loaded (11 products + 1 trailing empty row = 12)
        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 12

        # Step 6: Save the order
        dialog.btn_save.click()
        qtbot.wait(100)

        # Step 7: Verify order list now shows 4 orders (3 + 1 imported)
        assert order_view._model.rowCount() == 1

        # Step 8: Navigate back to product list
        mw._on_item_clicked("Lista de Produtos", "Notas")
        product_view = mw.centralWidget()  # type: ignore[union-attr]
        assert isinstance(product_view, ProductListView)

        # Step 9: Verify products from XML appear (4 existing + 11 from XML = 15)
        product_view.filter_month.setText("07/2026")
        product_view.btn_search.click()
        qtbot.wait(100)
        assert product_view._model.rowCount() == 11
