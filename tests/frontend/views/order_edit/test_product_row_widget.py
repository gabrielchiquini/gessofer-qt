from __future__ import annotations

from typing import List

from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QApplication

from frontend.views.order_edit.product_row_widget import ProductRowWidget
from models.output import Product
from tests.fixtures.order_edit_dialog_fixture import product_row_widget


class TestProductRowWidget:
    """TC-72 through TC-91: Verify ProductRowWidget behavior."""

    def test_auto_calculation_price_times_quantity(self, product_row_widget: ProductRowWidget,

                                                   ) -> None:
        tc_id: str = "TC-72"
        row = product_row_widget
        row.price_input.setText("100,00")

        row.quantity_input.setText("3")

        assert row.total_input.text() == "300,00"

    def test_auto_calculation_with_empty_price(self, product_row_widget: ProductRowWidget,

                                               ) -> None:
        tc_id: str = "TC-73"
        row = product_row_widget
        row.quantity_input.setText("5")

        assert row.total_input.text() == "0,00"

    def test_auto_calculation_with_empty_quantity(self, product_row_widget: ProductRowWidget,

                                                  ) -> None:
        tc_id: str = "TC-74"
        row = product_row_widget
        row.price_input.setText("50,00")

        assert row.total_input.text() == "0,00"

    def test_auto_calculation_both_empty(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-75"
        row = product_row_widget
        assert row.total_input.text() == "0,00"

    def test_is_empty_fully_empty(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-76"
        row = product_row_widget
        assert row.is_empty() is True

    def test_is_empty_partially_filled(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-77"
        row = product_row_widget
        row.name_input.setText("Cimento")
        assert row.is_empty() is False

    def test_is_empty_all_fields_filled(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-78"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("1")
        row.price_input.setText("50,00")
        assert row.is_empty() is False

    def test_get_product_data_returns_correct_data(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-79"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("2")
        row.price_input.setText("25,00")

        data = row.get_product_data("test-order", 1)
        assert data.name == "Cimento"
        assert data.quantity == 2
        assert data.price == 2500
        assert data.order_id == "test-order"

    def test_validate_required_if_filled_all_three(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-80"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("2")
        row.price_input.setText("25,00")

        valid, errors = row.validate(show_errors=True)
        assert valid is True
        assert errors == []

    def test_validate_required_if_filled_name_only(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-81"
        row = product_row_widget
        row.name_input.setText("Cimento")

        valid, errors = row.validate(show_errors=True)
        assert valid is False
        assert len(errors) >= 1

    def test_validate_required_if_filled_qty_only(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-82"
        row = product_row_widget
        row.quantity_input.setText("5")

        valid, errors = row.validate(show_errors=True)
        assert valid is False
        assert len(errors) >= 1

    def test_validate_required_if_filled_price_only(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-83"
        row = product_row_widget
        row.price_input.setText("99,99")

        valid, errors = row.validate(show_errors=True)
        assert valid is False
        assert len(errors) >= 1

    def test_validate_required_if_filled_name_plus_qty(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-84"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("2")

        valid, errors = row.validate(show_errors=True)
        assert valid is False
        assert len(errors) >= 1

    def test_validate_required_if_filled_all_empty(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-85"
        row = product_row_widget
        valid, errors = row.validate(show_errors=True)
        assert valid is True
        assert errors == []

    def test_warning_icon_displayed_with_warnings(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-86"
        row = product_row_widget
        row.set_warnings(["IPI diferenciado"])
        assert row.warning_icon.pixmap() is not None

    def test_error_label_hidden_when_valid(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-88"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("2")
        row.price_input.setText("25,00")
        row.validate(show_errors=True)

        assert row._error.isVisible() is False

    def test_error_label_visible_when_invalid(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-89"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.validate(show_errors=True)

        assert row._error.isVisible() is True

    def test_row_changed_signal_emitted(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-90"
        row = product_row_widget
        emitted: List[object] = []
        row.row_changed.connect(lambda: emitted.append(True))
        row.name_input.setText("Cimento")
        assert len(emitted) >= 1

class TestProductRowWidgetPreFilled:
    """TC-92: Verify ProductRowWidget pre-filled with Product data."""

    def test_row_pre_filled_with_product_data(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-92"
        row = product_row_widget

        product: Product = Product(id="pre-filled-prod", name="Cimento CP-II 50kg", quantity=3, price=25000,
                                   price_with_freight=25000, total=75000, order_id="test-order", item_ordinal=1, )

        # Create a new row with pre-filled data
        from PySide6.QtWidgets import QApplication
        new_row: ProductRowWidget = ProductRowWidget(parent=QApplication.activeWindow(), product_data=product)

        assert new_row.name_input.text() == "Cimento CP-II 50kg"
        assert new_row.quantity_input.text() == "3"
        assert new_row.price_input.text() == "250,00"
        assert new_row.total_input.text() == "750,00"
        assert new_row.price_with_freight_input.text() == "250,00"

        new_row.deleteLater()
