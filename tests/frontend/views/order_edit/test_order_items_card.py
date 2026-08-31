from __future__ import annotations

from typing import List

from di.injector_module import get_injector
from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from tests.fixtures.order_edit_dialog_fixture import order_edit_dialog_existing  # noqa: F401
from tests.fixtures.seed_data import ORDERS_DATA
from backend.utils.currency import cents_to_input, cents_to_view


class TestOrderItemsCardDataLoading:
    """TC-30 through TC-33: Verify product data loading from seeded orders."""

    def test_loads_order_a_products(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-30"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Order A: 2 products + 1 trailing = 3 rows
        assert len(rows) == 3, f"{tc_id}: expected 3 rows, got {len(rows)}"

        # Row 0: Cimento CP-II 50kg
        assert rows[0]._name_input.text() == ORDERS_DATA[0].products[0].name, \
            f"{tc_id}: row 0 name mismatch"
        assert rows[0]._quantity_input.text() == str(ORDERS_DATA[0].products[0].quantity), \
            f"{tc_id}: row 0 qty mismatch"
        assert rows[0]._price_input.text() == cents_to_input(ORDERS_DATA[0].products[0].price), \
            f"{tc_id}: row 0 price mismatch"
        # total_with_freight = price_with_freight × quantity
        expected_total_0: int = ORDERS_DATA[0].products[0].price_with_freight * ORDERS_DATA[0].products[0].quantity
        assert rows[0]._total_with_freight_input.text() == cents_to_input(expected_total_0), \
            f"{tc_id}: row 0 total mismatch"
        assert rows[0]._price_with_freight_input.text() == cents_to_input(ORDERS_DATA[0].products[0].price_with_freight), \
            f"{tc_id}: row 0 price_with_freight mismatch"

        # Row 1: Cimento CP-II 1kg
        assert rows[1]._name_input.text() == ORDERS_DATA[0].products[1].name, \
            f"{tc_id}: row 1 name mismatch"
        assert rows[1]._quantity_input.text() == str(ORDERS_DATA[0].products[1].quantity), \
            f"{tc_id}: row 1 qty mismatch"
        assert rows[1]._price_input.text() == cents_to_input(ORDERS_DATA[0].products[1].price), \
            f"{tc_id}: row 1 price mismatch"
        # total_with_freight = price_with_freight × quantity
        expected_total_1: int = ORDERS_DATA[0].products[1].price_with_freight * ORDERS_DATA[0].products[1].quantity
        assert rows[1]._total_with_freight_input.text() == cents_to_input(expected_total_1), \
            f"{tc_id}: row 1 total mismatch"
        assert rows[1]._price_with_freight_input.text() == cents_to_input(ORDERS_DATA[0].products[1].price_with_freight), \
            f"{tc_id}: row 1 price_with_freight mismatch"

        # Row 2: trailing empty row
        assert rows[2].is_empty() is True, f"{tc_id}: row 2 should be empty"

    def test_loads_order_b_products(
            self,
            temp_engine: object,
            qtbot: object,
    ) -> None:
        tc_id: str = "TC-31"
        injector = get_injector()
        factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
        dialog: OrderEditDialog = factory(parent=None, order_id="order-b", order=None)
        qtbot.addWidget(dialog)
        dialog.show()

        try:
            rows = dialog.items_card.get_product_rows()
            # Order B: 1 product + 1 trailing = 2 rows
            assert len(rows) == 2, f"{tc_id}: expected 2 rows, got {len(rows)}"

            assert rows[0]._name_input.text() == ORDERS_DATA[1].products[0].name, \
                f"{tc_id}: row 0 name mismatch"
            assert rows[0]._quantity_input.text() == str(ORDERS_DATA[1].products[0].quantity), \
                f"{tc_id}: row 0 qty mismatch"
            assert rows[0]._price_input.text() == cents_to_input(ORDERS_DATA[1].products[0].price), \
                f"{tc_id}: row 0 price mismatch"
            # total_with_freight = price_with_freight × quantity
            expected_total_b: int = ORDERS_DATA[1].products[0].price_with_freight * ORDERS_DATA[1].products[0].quantity
            assert rows[0]._total_with_freight_input.text() == cents_to_input(expected_total_b), \
                f"{tc_id}: row 0 total mismatch"
            assert rows[0]._price_with_freight_input.text() == cents_to_input(ORDERS_DATA[1].products[0].price_with_freight), \
                f"{tc_id}: row 0 price_with_freight mismatch"
        finally:
            dialog.deleteLater()

    def test_total_label_shows_correct_total(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-32"
        dialog = order_edit_dialog_existing
        expected_products_total: int = sum(p.total for p in ORDERS_DATA[0].products)
        expected: str = f"Total dos produtos: R$ 255,00\nTotal da nota: R$ 315,00"
        actual: str = dialog.items_card._products_total_label.text()
        assert actual == expected, f"{tc_id}: expected {expected!r}, got {actual!r}"

    def test_set_order_data_emits_order_changed(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-33"
        dialog = order_edit_dialog_existing
        emitted: List[object] = []
        dialog.items_card.order_changed.connect(lambda: emitted.append(True))
        dialog.items_card._product_rows[0]._name_input.setText("Produto alterado")
        assert len(emitted) >= 1, f"{tc_id}: order_changed not emitted"


class TestOrderItemsCardAddRow:
    """TC-34 through TC-36: Verify add_row behavior."""

    def test_add_row_increases_row_count(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-34"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        initial_count: int = len(rows)

        dialog.items_card.add_row()

        rows = dialog.items_card.get_product_rows()
        assert len(rows) == initial_count + 1, \
            f"{tc_id}: expected {initial_count + 1} rows, got {len(rows)}"

    def test_add_row_emits_row_added_signal(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-35"
        dialog = order_edit_dialog_existing
        emitted: List[object] = []
        dialog.items_card.row_added.connect(lambda r: emitted.append(r))

        dialog.items_card.add_row()

        assert len(emitted) == 1, f"{tc_id}: expected 1 row_added signal, got {len(emitted)}"

    def test_add_row_creates_empty_row(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-36"
        dialog = order_edit_dialog_existing
        dialog.items_card.add_row()

        rows = dialog.items_card.get_product_rows()
        new_row = rows[-1]
        assert new_row.is_empty() is True, f"{tc_id}: new row should be empty"


class TestOrderItemsCardDeleteRow:
    """TC-37 through TC-39: Verify delete_row behavior."""

    def test_delete_row_via_button_click(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-37"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Click delete on row 0
        rows[0].delete_button.click()

        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 2, f"{tc_id}: expected 2 rows, got {len(rows)}"

        # Last row delete button should be disabled
        assert rows[-1].delete_button.isEnabled() is False, \
            f"{tc_id}: last row delete should be disabled"

    def test_delete_button_state_after_delete(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-38"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Delete row 0
        rows[0].delete_button.click()

        rows = dialog.items_card.get_product_rows()
        # Last row (trailing) should be disabled
        assert rows[-1].delete_button.isEnabled() is False, \
            f"{tc_id}: last row delete should be disabled"
        # Remaining non-last rows should be enabled
        if len(rows) > 1:
            assert rows[0].delete_button.isEnabled() is True, \
                f"{tc_id}: non-last row delete should be enabled"

    def test_delete_row_via_signal(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-39"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        initial_count: int = len(rows)

        # Simulate delete_pressed on row 1
        rows[1].delete_pressed.emit()

        rows = dialog.items_card.get_product_rows()
        assert len(rows) == initial_count - 1, \
            f"{tc_id}: expected {initial_count - 1} rows, got {len(rows)}"


class TestOrderItemsCardAutoAddRow:
    """TC-40 through TC-42: Verify auto-add row when trailing row is filled."""

    def test_auto_add_when_trailing_row_filled(
            self,
            order_edit_dialog_existing: OrderEditDialog,
            qtbot: object,
    ) -> None:
        tc_id: str = "TC-40"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        trailing = rows[-1]

        # Fill trailing row
        trailing._name_input.setText("Novo produto")
        trailing._quantity_input.setText("1")
        trailing._price_input.setText("100,00")

        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 4, f"{tc_id}: expected 4 rows, got {len(rows)}"

    def test_auto_add_preserves_filled_row_data(
            self,
            order_edit_dialog_existing: OrderEditDialog,
            qtbot: object,
    ) -> None:
        tc_id: str = "TC-41"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        trailing = rows[-1]

        # Fill trailing row
        trailing._name_input.setText("Produto fillado")
        trailing._quantity_input.setText("3")
        trailing._price_input.setText("50,00")

        rows = dialog.items_card.get_product_rows()
        # The previously trailing row (now row 2) should still have data
        assert rows[2]._name_input.text() == "Produto fillado", \
            f"{tc_id}: name should be preserved"
        assert rows[2]._quantity_input.text() == "3", \
            f"{tc_id}: qty should be preserved"
        assert rows[2]._price_input.text() == "50,00", \
            f"{tc_id}: price should be preserved"

    def test_auto_add_new_row_is_empty(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-42"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        trailing = rows[-1]

        # Fill trailing row
        trailing._name_input.setText("Produto fillado")
        trailing._quantity_input.setText("1")
        trailing._price_input.setText("10,00")

        rows = dialog.items_card.get_product_rows()
        # New last row should be empty
        assert rows[-1].is_empty() is True, f"{tc_id}: new trailing row should be empty"


class TestOrderItemsCardTotalCalculation:
    """TC-43 through TC-46: Verify total label updates."""

    def test_total_updates_on_price_change(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-43"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Change row 0 price from 250,00 to 300,00
        new_total: int = 30000 + ORDERS_DATA[0].products[1].total
        rows[0]._price_input.setText("300,00")

        expected: str = f"Total dos produtos: R$ 305,00\nTotal da nota: R$ 365,00"
        actual: str = dialog.items_card._products_total_label.text()
        assert actual == expected, f"{tc_id}: expected {expected!r}, got {actual!r}"

    def test_total_updates_on_quantity_change(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-44"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Change row 0 qty from 1 to 2
        new_total: int = ORDERS_DATA[0].products[0].price * 2 + ORDERS_DATA[0].products[1].total
        rows[0]._quantity_input.setText("2")

        expected: str = f"Total dos produtos: R$ 505,00\nTotal da nota: R$ 565,00"
        actual: str = dialog.items_card._products_total_label.text()
        assert actual == expected, f"{tc_id}: expected {expected!r}, got {actual!r}"

    def test_total_excludes_trailing_empty_row(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-45"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Fill trailing row with data
        empty_row = rows[-1]
        empty_row._name_input.setText("Produto extra")
        empty_row._quantity_input.setText("1")
        empty_row._price_input.setText("100,00")

        # After auto-add, there should be 4 rows
        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 4

        existing_total: int = sum(p.total for p in ORDERS_DATA[0].products)
        new_total: int = existing_total + 10000
        expected: str = f"Total dos produtos: R$ 355,00\nTotal da nota: R$ 415,00"
        actual: str = dialog.items_card._products_total_label.text()
        assert actual == expected, f"{tc_id}: expected {expected!r}, got {actual!r}"

    def test_total_is_zero_with_empty_rows(
            self,
            order_edit_dialog_blank: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-46"
        dialog = order_edit_dialog_blank
        expected: str = "Total dos produtos: 0,00"
        actual: str = dialog.items_card._products_total_label.text()
        assert actual == expected, f"{tc_id}: expected {expected!r}, got {actual!r}"


class TestOrderItemsCardProductsList:
    """TC-47 through TC-49: Verify get_products_list behavior."""

    def test_get_products_list_excludes_trailing_row(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-47"
        dialog = order_edit_dialog_existing
        products = dialog.items_card.get_products_list("test-order")
        # Order A: 2 products, trailing excluded
        assert len(products) == 2, f"{tc_id}: expected 2 products, got {len(products)}"

    def test_get_products_list_returns_correct_data(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-48"
        dialog = order_edit_dialog_existing
        products = dialog.items_card.get_products_list("order-a")

        assert products[0].name == "Cimento CP-II 50kg", \
            f"{tc_id}: product 0 name mismatch"
        assert products[0].quantity == 1, \
            f"{tc_id}: product 0 qty mismatch"
        assert products[0].price == 25000, \
            f"{tc_id}: product 0 price mismatch"
        assert products[0].total == 25000, \
            f"{tc_id}: product 0 total mismatch"

        assert products[1].name == "Cimento CP-II 1kg", \
            f"{tc_id}: product 1 name mismatch"
        assert products[1].quantity == 1, \
            f"{tc_id}: product 1 qty mismatch"
        assert products[1].price == 500, \
            f"{tc_id}: product 1 price mismatch"
        assert products[1].total == 500, \
            f"{tc_id}: product 1 total mismatch"

class TestOrderItemsCardValidation:
    """TC-50 through TC-54: Row validation tests."""

    def test_partial_row_name_only(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-50"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        # Fill only name in trailing row
        rows[-1]._name_input.setText("Só nome")

        valid, errors = dialog.items_card.validate(show_errors=True)
        assert valid is False, f"{tc_id}: expected invalid"
        assert len(errors) >= 1, f"{tc_id}: expected at least 1 error"
        assert "Quantidade" in errors[0] or "Preço" in errors[0], \
            f"{tc_id}: expected qty/price error, got {errors}"

    def test_partial_row_quantity_only(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-51"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        # Fill only quantity in trailing row
        rows[-1]._quantity_input.setText("5")

        valid, errors = dialog.items_card.validate(show_errors=True)
        assert valid is False, f"{tc_id}: expected invalid"
        assert len(errors) >= 1, f"{tc_id}: expected at least 1 error"

    def test_partial_row_price_only(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-52"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        # Fill only price in trailing row
        rows[-1]._price_input.setText("99,99")

        valid, errors = dialog.items_card.validate(show_errors=True)
        assert valid is False, f"{tc_id}: expected invalid"
        assert len(errors) >= 1, f"{tc_id}: expected at least 1 error"

    def test_all_valid_rows_pass(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-53"
        dialog = order_edit_dialog_existing
        valid, errors = dialog.items_card.validate(show_errors=True)
        # Order A rows are valid (filled), trailing empty row is valid
        assert valid is True, f"{tc_id}: expected valid, got errors {errors}"
        assert errors == [], f"{tc_id}: expected no errors"

    def test_all_empty_rows_pass(
            self,
            order_edit_dialog_blank: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-54"
        dialog = order_edit_dialog_blank
        valid, errors = dialog.items_card.validate(show_errors=True)
        # Blank dialog has only trailing empty row — valid
        assert valid is True, f"{tc_id}: expected valid, got errors {errors}"
        assert errors == [], f"{tc_id}: expected no errors"

    def test_mixed_valid_invalid_rows(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        tc_id: str = "TC-55"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()
        # Fill only name in trailing row → invalid
        rows[-1]._name_input.setText("Produto inválido")

        valid, errors = dialog.items_card.validate(show_errors=True)
        assert valid is False, f"{tc_id}: expected invalid"
        # Should have errors from the trailing row
        assert len(errors) >= 1, f"{tc_id}: expected at least 1 error"
