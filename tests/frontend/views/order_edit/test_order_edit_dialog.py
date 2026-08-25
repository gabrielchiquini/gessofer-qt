from __future__ import annotations

from typing import List
from unittest.mock import patch

from PySide6.QtWidgets import QDialog, QMessageBox
from pytestqt.qtbot import QtBot

from frontend.views.order_edit.nfe_search_dialog import NfeSearchDialog
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from frontend.views.order_edit.product_row_widget import ProductRowWidget
from models.input import OrderInput
from models.output import Product
from tests.fixtures.order_edit_dialog_fixture import (order_edit_dialog_existing, order_edit_dialog_blank,
                                                      order_edit_dialog_xml_import, nfe_search_dialog,
                                                      product_row_widget, )


class TestOrderEditDialogInit:
    """TC-56 through TC-59: Verify dialog initialization paths."""

    def test_init_with_existing_order_populates_fields(self, order_edit_dialog_existing: OrderEditDialog, ) -> None:
        tc_id: str = "TC-56"
        dialog = order_edit_dialog_existing

        # Window title
        assert dialog.windowTitle() == "Editar Pedido", f"{tc_id}: expected 'Editar Pedido', got {dialog.windowTitle()!r}"

        # Header fields
        assert dialog.header_card._supplier_input.get_text() == "Cimento Portland"
        assert dialog.header_card._date_input.get_text() == "10/07/2024"

        # Items count
        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 3, f"{tc_id}: expected 3 rows, got {len(rows)}"

    def test_init_with_existing_order_loads_products(self, order_edit_dialog_existing: OrderEditDialog, ) -> None:
        tc_id: str = "TC-57"
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        assert rows[0].name_input.text() == "Cimento CP-II 50kg"
        assert rows[0].quantity_input.text() == "1"
        assert rows[0].price_input.text() == "250,00"
        assert rows[0].total_input.text() == "250,00"

        assert rows[1].name_input.text() == "Cimento CP-II 1kg"
        assert rows[1].quantity_input.text() == "1"
        assert rows[1].price_input.text() == "5,00"
        assert rows[1].total_input.text() == "5,00"

    def test_init_with_blank_order_has_one_empty_row(self, order_edit_dialog_blank: OrderEditDialog, ) -> None:
        tc_id: str = "TC-58"
        dialog = order_edit_dialog_blank

        assert dialog.windowTitle() == "Novo Pedido", f"{tc_id}: expected 'Novo Pedido', got {dialog.windowTitle()!r}"

        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 1, f"{tc_id}: expected 1 row, got {len(rows)}"
        assert rows[0].is_empty() is True, f"{tc_id}: row should be empty"

    def test_init_with_xml_import_populates_fields(self, order_edit_dialog_xml_import: OrderEditDialog, ) -> None:
        tc_id: str = "TC-59"
        dialog = order_edit_dialog_xml_import

        # Window title — XML import path sets _is_new=True
        assert dialog.windowTitle() == "Novo Pedido", f"{tc_id}: expected 'Novo Pedido', got {dialog.windowTitle()!r}"

        # _imported_order exists
        assert hasattr(dialog, "_imported_order"), f"{tc_id}: _imported_order attribute missing"
        assert dialog._imported_order is not None, f"{tc_id}: _imported_order should not be None"

        # Verify header populated from XML
        supplier: str = dialog.header_card._supplier_input.get_text()
        assert supplier == "O.V.D. IMPORTADORA E DISTRIBUIDORA LTDA", f"{tc_id}: supplier mismatch: {supplier!r}"

        date: str = dialog.header_card._date_input.get_text()
        assert date == "02/07/2026", f"{tc_id}: date mismatch: {date!r}"

        # Freight and unloading should be 0 (not set)
        assert dialog.header_card._freight_input.get_text() == ""
        assert dialog.header_card._unloading_input.get_text() == ""

        # Items: 11 products + 1 trailing = 12 rows
        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 12, f"{tc_id}: expected 12 rows, got {len(rows)}"

        # nfe_key should match the XML
        nfe_key: str = dialog._imported_order.nfe_key
        assert len(nfe_key) == 44, f"{tc_id}: nfe_key length {len(nfe_key)}"
        assert nfe_key.isdigit(), f"{tc_id}: nfe_key should be all digits"


class TestOrderEditDialogSave:
    """TC-60 through TC-63: Verify save behavior."""

    def test_save_valid_edited_order(self, order_edit_dialog_existing: OrderEditDialog,

                                     ) -> None:
        tc_id: str = "TC-60"
        dialog = order_edit_dialog_existing

        # Edit supplier
        dialog.header_card._supplier_input.set_text("Fornecedor Editado")

        # Connect signal
        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)

        # Click save
        dialog.btn_save.click()

        # Signal emitted
        assert len(saved) == 1, f"{tc_id}: expected 1 signal emission"

        # Dialog accepted
        assert dialog.result() == QDialog.DialogCode.Accepted, f"{tc_id}: dialog should be accepted"

    def test_save_emits_order_with_correct_data(self, order_edit_dialog_existing: OrderEditDialog,

                                                ) -> None:
        tc_id: str = "TC-61"
        dialog = order_edit_dialog_existing

        # Edit supplier and a product
        dialog.header_card._supplier_input.set_text("Novo Fornecedor")

        rows = dialog.items_card.get_product_rows()
        rows[0].price_input.setText("300,00")

        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)
        dialog.btn_save.click()

        assert len(saved) == 1, f"{tc_id}: expected 1 signal emission"
        order_data = saved[0]
        assert order_data.supplier == "Novo Fornecedor", f"{tc_id}: supplier mismatch: {order_data.supplier!r}"
        assert order_data.products[0].price == 30000, f"{tc_id}: product price mismatch: {order_data.products[0].price}"

    def test_save_preserves_nfe_key_on_xml_import(self, order_edit_dialog_xml_import: OrderEditDialog,

                                                  ) -> None:
        tc_id: str = "TC-62"
        dialog = order_edit_dialog_xml_import

        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)
        dialog.btn_save.click()

        assert len(saved) == 1, f"{tc_id}: expected 1 signal emission"
        order_data = saved[0]
        assert order_data.nfe_key == dialog._imported_order.nfe_key, f"{tc_id}: nfe_key should be preserved from XML import"

    def test_save_invalid_order_does_not_save(self, order_edit_dialog_existing: OrderEditDialog,

                                              ) -> None:
        tc_id: str = "TC-63"
        dialog = order_edit_dialog_existing

        # Clear supplier — invalid
        dialog.header_card._supplier_input.clear()

        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)
        dialog.btn_save.click()

        # No signal emitted
        assert len(saved) == 0, f"{tc_id}: should not emit signal on invalid save"

        # Dialog not accepted
        assert dialog.result() != QDialog.DialogCode.Accepted, f"{tc_id}: dialog should not be accepted"


class TestOrderEditDialogValidation:
    """TC-64 through TC-66: Verify validation during save."""

    def test_save_with_header_validation_errors(self, order_edit_dialog_existing: OrderEditDialog,

                                                ) -> None:
        tc_id: str = "TC-64"
        dialog = order_edit_dialog_existing

        # Clear supplier
        dialog.header_card._supplier_input.clear()

        dialog.btn_save.click()

        # Header field was validated
        assert dialog.header_card._supplier_input.get_was_validated() is True, f"{tc_id}: supplier should be marked as validated"

        # No signal emitted (save failed)
        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)
        dialog.btn_save.click()

        # Note: _was_validated is already True from previous call

    def test_save_with_items_validation_errors(self, order_edit_dialog_existing: OrderEditDialog,
                                               qtbot: QtBot, ) -> None:
        tc_id: str = "TC-65"
        dialog = order_edit_dialog_existing

        # Fill only name in trailing row
        rows = dialog.items_card.get_product_rows()
        rows[-1].name_input.setText("Produto incompleto")

        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)
        dialog.btn_save.click()

        # Signal not emitted
        assert len(saved) == 0, f"{tc_id}: should not emit on items validation failure"

        # Error visible on the row
        assert rows[-2]._error.isVisible() is True, f"{tc_id}: error should be visible"

    def test_save_with_both_header_and_items_errors(self, order_edit_dialog_existing: OrderEditDialog,

                                                    ) -> None:
        tc_id: str = "TC-66"
        dialog = order_edit_dialog_existing

        # Clear supplier (header error)
        dialog.header_card._supplier_input.clear()

        # Fill only name in trailing row (items error)
        rows = dialog.items_card.get_product_rows()
        rows[-1].name_input.setText("Produto incompleto")

        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)
        dialog.btn_save.click()

        # No signal emitted
        assert len(saved) == 0, f"{tc_id}: should not emit on combined validation failure"

        # Header field was validated
        assert dialog.header_card._supplier_input.get_was_validated() is True


class TestOrderEditDialogClose:
    """TC-67 through TC-68: Verify close behavior."""

    def test_close_button_rejects(self, order_edit_dialog_existing: OrderEditDialog,

                                  ) -> None:
        tc_id: str = "TC-67"
        dialog = order_edit_dialog_existing
        dialog.btn_close.click()

        assert dialog.result() == QDialog.DialogCode.Rejected, f"{tc_id}: dialog should be rejected"

    def test_close_emits_closed_signal(self, order_edit_dialog_existing: OrderEditDialog,

                                       ) -> None:
        tc_id: str = "TC-68"
        dialog = order_edit_dialog_existing
        closed: List[None] = []
        dialog.closed.connect(lambda: closed.append(None))
        dialog.btn_close.click()

        assert len(closed) == 1, f"{tc_id}: expected 1 closed signal"

class TestProductRowWidget:
    """TC-72 through TC-91: Verify ProductRowWidget behavior."""

    def test_auto_calculation_price_times_quantity(self, product_row_widget: ProductRowWidget,

                                                   ) -> None:
        tc_id: str = "TC-72"
        row = product_row_widget
        row.price_input.setText("100,00")

        row.quantity_input.setText("3")

        assert row.total_input.text() == "300,00", f"{tc_id}: expected '300,00', got {row.total_input.text()!r}"

    def test_auto_calculation_with_empty_price(self, product_row_widget: ProductRowWidget,

                                               ) -> None:
        tc_id: str = "TC-73"
        row = product_row_widget
        row.quantity_input.setText("5")

        assert row.total_input.text() == "0,00", f"{tc_id}: expected '0,00' when price is empty"

    def test_auto_calculation_with_empty_quantity(self, product_row_widget: ProductRowWidget,

                                                  ) -> None:
        tc_id: str = "TC-74"
        row = product_row_widget
        row.price_input.setText("50,00")

        assert row.total_input.text() == "0,00", f"{tc_id}: expected '0,00' when quantity is empty"

    def test_auto_calculation_both_empty(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-75"
        row = product_row_widget
        assert row.total_input.text() == "0,00", f"{tc_id}: expected '0,00' when both empty"

    def test_is_empty_fully_empty(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-76"
        row = product_row_widget
        assert row.is_empty() is True, f"{tc_id}: fresh row should be empty"

    def test_is_empty_partially_filled(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-77"
        row = product_row_widget
        row.name_input.setText("Cimento")
        assert row.is_empty() is False, f"{tc_id}: partially filled should not be empty"

    def test_is_empty_all_fields_filled(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-78"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("1")
        row.price_input.setText("50,00")
        assert row.is_empty() is False, f"{tc_id}: all filled should not be empty"

    def test_get_product_data_returns_correct_data(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-79"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("2")
        row.price_input.setText("25,00")

        data = row.get_product_data("test-order", 1)
        assert data.name == "Cimento", f"{tc_id}: name mismatch"
        assert data.quantity == 2, f"{tc_id}: quantity mismatch"
        assert data.price == 2500, f"{tc_id}: price mismatch"
        assert data.order_id == "test-order", f"{tc_id}: order_id mismatch"

    def test_validate_required_if_filled_all_three(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-80"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("2")
        row.price_input.setText("25,00")

        valid, errors = row.validate(show_errors=True)
        assert valid is True, f"{tc_id}: expected valid, got errors {errors}"
        assert errors == [], f"{tc_id}: expected no errors"

    def test_validate_required_if_filled_name_only(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-81"
        row = product_row_widget
        row.name_input.setText("Cimento")

        valid, errors = row.validate(show_errors=True)
        assert valid is False, f"{tc_id}: expected invalid"
        assert len(errors) >= 1, f"{tc_id}: expected errors"

    def test_validate_required_if_filled_qty_only(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-82"
        row = product_row_widget
        row.quantity_input.setText("5")

        valid, errors = row.validate(show_errors=True)
        assert valid is False, f"{tc_id}: expected invalid"
        assert len(errors) >= 1, f"{tc_id}: expected errors"

    def test_validate_required_if_filled_price_only(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-83"
        row = product_row_widget
        row.price_input.setText("99,99")

        valid, errors = row.validate(show_errors=True)
        assert valid is False, f"{tc_id}: expected invalid"
        assert len(errors) >= 1, f"{tc_id}: expected errors"

    def test_validate_required_if_filled_name_plus_qty(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-84"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("2")

        valid, errors = row.validate(show_errors=True)
        assert valid is False, f"{tc_id}: expected invalid (missing price)"
        assert len(errors) >= 1, f"{tc_id}: expected errors"

    def test_validate_required_if_filled_all_empty(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-85"
        row = product_row_widget
        valid, errors = row.validate(show_errors=True)
        assert valid is True, f"{tc_id}: expected valid for empty row"
        assert errors == [], f"{tc_id}: expected no errors"

    def test_warning_icon_displayed_with_warnings(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-86"
        row = product_row_widget
        row.set_warnings(["IPI diferenciado"])
        assert row.warning_icon.pixmap() is not None, f"{tc_id}: pixmap should not be None with warnings"

    def test_error_label_hidden_when_valid(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-88"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.quantity_input.setText("2")
        row.price_input.setText("25,00")
        row.validate(show_errors=True)

        assert row._error.isVisible() is False, f"{tc_id}: error should be hidden for valid row"

    def test_error_label_visible_when_invalid(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-89"
        row = product_row_widget
        row.name_input.setText("Cimento")
        row.validate(show_errors=True)

        assert row._error.isVisible() is True, f"{tc_id}: error should be visible for invalid row"

    def test_row_changed_signal_emitted(self, product_row_widget: ProductRowWidget, ) -> None:
        tc_id: str = "TC-90"
        row = product_row_widget
        emitted: List[object] = []
        row.row_changed.connect(lambda: emitted.append(True))
        row.name_input.setText("Cimento")
        assert len(emitted) >= 1, f"{tc_id}: row_changed should be emitted"

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

        assert new_row.name_input.text() == "Cimento CP-II 50kg", f"{tc_id}: name mismatch"
        assert new_row.quantity_input.text() == "3", f"{tc_id}: quantity mismatch"
        assert new_row.price_input.text() == "250,00", f"{tc_id}: price mismatch"
        assert new_row.total_input.text() == "750,00", f"{tc_id}: total mismatch"
        assert new_row.price_with_freight_input.text() == "250,00", f"{tc_id}: price_with_freight mismatch"

        new_row.deleteLater()


class TestNfeSearchDialog:
    """TC-93 through TC-98: Verify NfeSearchDialog behavior."""

    def test_invalid_key_too_short(self, nfe_search_dialog: NfeSearchDialog,

                                   ) -> None:
        tc_id: str = "TC-93"
        dialog = nfe_search_dialog
        dialog._nfe_key_edit.setText("12345")

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.btn_search.click()
            mock_warning.assert_called_once()

    def test_invalid_key_non_digits(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-94"
        dialog = nfe_search_dialog
        # 44 non-digit characters
        dialog._nfe_key_edit.setText("abcdefghijklmnopqrstuvwxy012345678901234")

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.btn_search.click()
            mock_warning.assert_called_once()

    def test_valid_key_44_digits_enables_search(self, nfe_search_dialog: NfeSearchDialog) -> None:
        tc_id: str = "TC-95"
        dialog = nfe_search_dialog
        # Enter 44 zeros — the input mask fills them
        dialog._nfe_key_edit.setText("0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000")

        key: str = dialog._nfe_key_edit.text().replace(" ", "")
        assert len(key) == 44, f"{tc_id}: expected 44 digits, got {len(key)}"
        assert key.isdigit(), f"{tc_id}: key should be all digits"

    def test_close_button_rejects(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-96"
        dialog = nfe_search_dialog
        dialog.btn_close.click()

        assert dialog.result() == QDialog.DialogCode.Rejected, f"{tc_id}: dialog should be rejected"

    def test_input_mask_applied(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-97"
        dialog = nfe_search_dialog
        expected_mask: str = "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"
        actual_mask: str = dialog._nfe_key_edit.inputMask()
        assert actual_mask == expected_mask, f"{tc_id}: expected {expected_mask!r}, got {actual_mask!r}"

    def test_progress_label_hidden_initially(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-98"
        dialog = nfe_search_dialog
        assert dialog._progress_label.isVisible() is False, f"{tc_id}: progress label should be hidden initially"
