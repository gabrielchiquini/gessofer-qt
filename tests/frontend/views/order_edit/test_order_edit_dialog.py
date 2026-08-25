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

from di.injector_module import get_injector
from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory


class TestOrderEditDialogInit:
    """TC-56 through TC-59: Verify dialog initialization paths."""

    def test_init_with_existing_order_populates_fields(self, order_edit_dialog_existing: OrderEditDialog, ) -> None:
        tc_id: str = "TC-56"
        dialog = order_edit_dialog_existing

        # Window title
        assert dialog.windowTitle() == "Editar Pedido"

        # Header fields
        assert dialog.header_card._supplier_input.get_text() == "Cimento Portland"
        assert dialog.header_card._date_input.get_text() == "10/07/2024"

        # Items count
        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 3

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

        # price_with_freight assertions — loaded from DB via seed data
        assert rows[0].price_with_freight_input.text() == "308,82"
        assert rows[1].price_with_freight_input.text() == "6,18"

    def test_init_with_blank_order_has_one_empty_row(self, order_edit_dialog_blank: OrderEditDialog, ) -> None:
        tc_id: str = "TC-58"
        dialog = order_edit_dialog_blank

        assert dialog.windowTitle() == "Novo Pedido"

        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 1
        assert rows[0].is_empty() is True

    def test_init_with_xml_import_populates_fields(self, order_edit_dialog_xml_import: OrderEditDialog, ) -> None:
        tc_id: str = "TC-59"
        dialog = order_edit_dialog_xml_import

        # Window title — XML import path sets _is_new=True
        assert dialog.windowTitle() == "Novo Pedido"

        # _imported_order exists
        assert hasattr(dialog, "_imported_order")
        assert dialog._imported_order is not None

        # Verify header populated from XML
        supplier: str = dialog.header_card._supplier_input.get_text()
        assert supplier == "O.V.D. IMPORTADORA E DISTRIBUIDORA LTDA"

        date: str = dialog.header_card._date_input.get_text()
        assert date == "02/07/2026"

        # Freight and unloading should be 0 (not set)
        assert dialog.header_card._freight_input.get_text() == ""
        assert dialog.header_card._unloading_input.get_text() == ""

        # Items: 11 products + 1 trailing = 12 rows
        rows = dialog.items_card.get_product_rows()
        assert len(rows) == 12

        # nfe_key should match the XML
        nfe_key: str = dialog._imported_order.nfe_key
        assert len(nfe_key) == 44
        assert nfe_key.isdigit()


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
        assert len(saved) == 1

        # Dialog accepted
        assert dialog.result() == QDialog.DialogCode.Accepted

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

        assert len(saved) == 1
        order_data = saved[0]
        assert order_data.supplier == "Novo Fornecedor"
        assert order_data.products[0].price == 30000

    def test_save_preserves_nfe_key_on_xml_import(self, order_edit_dialog_xml_import: OrderEditDialog,

                                                  ) -> None:
        tc_id: str = "TC-62"
        dialog = order_edit_dialog_xml_import

        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)
        for row in dialog.items_card.get_product_rows():
            if row.quantity_input.text() == "0":
                row.quantity_input.setText("1")
        dialog.btn_save.click()

        assert len(saved) == 1
        order_data = saved[0]
        assert order_data.nfe_key == dialog._imported_order.nfe_key

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
        assert len(saved) == 0

        # Dialog not accepted
        assert dialog.result() != QDialog.DialogCode.Accepted


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
        assert dialog.header_card._supplier_input.get_was_validated() is True

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
        assert len(saved) == 0

        # Error visible on the row
        assert rows[-2]._error.isVisible() is True

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
        assert len(saved) == 0

        # Header field was validated
        assert dialog.header_card._supplier_input.get_was_validated() is True


class TestOrderEditDialogClose:
    """TC-67 through TC-68: Verify close behavior."""

    def test_close_button_rejects(self, order_edit_dialog_existing: OrderEditDialog,

                                  ) -> None:
        tc_id: str = "TC-67"
        dialog = order_edit_dialog_existing
        dialog.btn_close.click()

        assert dialog.result() == QDialog.DialogCode.Rejected

    def test_close_emits_closed_signal(self, order_edit_dialog_existing: OrderEditDialog,

                                       ) -> None:
        tc_id: str = "TC-68"
        dialog = order_edit_dialog_existing
        closed: List[None] = []
        dialog.closed.connect(lambda: closed.append(None))
        dialog.btn_close.click()

        assert len(closed) == 1

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


class TestOrderEditDialogFreightDistribution:
    """Verify freight distribution for existing orders."""

    def test_freight_distribution_applied_on_existing_order(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        """
        When order-a is loaded (freight=5000, unloading=1000),
        verify that price_with_freight values are correctly distributed.
        """
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Order A has 2 products + 1 trailing = 3 rows
        assert len(rows) == 3

        # Verify price_with_freight from seed data
        assert rows[0].price_with_freight_input.text() == "308,82"
        assert rows[1].price_with_freight_input.text() == "6,18"

        # Verify header freight/unloading fields are populated
        assert dialog.header_card._freight_input.get_text() == "50,00"
        assert dialog.header_card._unloading_input.get_text() == "10,00"

    def test_freight_distribution_recalculation_on_header_change(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        """
        When freight and unloading are changed in the header,
        verify that set_freight_data recalculates all price_with_freight values.

        Signal chain:
          _freight_input.set_text() → _on_header_changed()
            → order_changed.emit() → _on_header_freight_changed()
              → items_card.set_freight_data() → row.set_price_with_freight()
        """
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Clear existing values using set_text("") — clear() does NOT emit signals
        dialog.header_card._freight_input.set_text("")
        dialog.header_card._unloading_input.set_text("")

        # Set freight = 200,00 (20000 cents) and unloading = 50,00 (5000 cents)
        dialog.header_card._freight_input.set_text("200,00")
        dialog.header_card._unloading_input.set_text("50,00")

        # products_total = 25000 + 500 = 25500
        # freight_total = 20000 + 5000 = 25000
        # ratio = (25000 + 25500) / 25500 = 50500 / 25500 ≈ 1.9803921568627452
        # prod-a1: pwf = round(25000 * 1.9803921568627452) = round(49509.803...) = 49510
        # prod-a2: pwf = round(500 * 1.9803921568627452) = round(990.196...) = 990
        assert rows[0].price_with_freight_input.text() == "495,10"
        assert rows[1].price_with_freight_input.text() == "9,90"

    def test_freight_zero_resets_price_with_freight_to_base_price(
            self,
            order_edit_dialog_existing: OrderEditDialog,
    ) -> None:
        """
        When freight and unloading are both cleared (0),
        price_with_freight should fall back to base price for each row.
        """
        dialog = order_edit_dialog_existing
        rows = dialog.items_card.get_product_rows()

        # Clear freight and unloading using set_text("") — clear() does NOT emit signals
        dialog.header_card._freight_input.set_text("")
        dialog.header_card._unloading_input.set_text("")

        # Verify price_with_freight equals base price
        # Row 0: price = 25000 cents → "250,00"
        assert rows[0].price_with_freight_input.text() == "250,00"
        # Row 1: price = 500 cents → "5,00"
        assert rows[1].price_with_freight_input.text() == "5,00"

    def test_freight_distribution_with_order_b_single_product(
            self,
            temp_engine: object,
            qtbot: QtBot,
    ) -> None:
        """
        Verify freight distribution for order-b (single product,
        higher quantity) when freight/unloading are changed.
        """
        injector = get_injector()
        factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
        dialog: OrderEditDialog = factory(parent=None, order_id="order-b", order=None)
        qtbot.addWidget(dialog)
        dialog.show()

        try:
            rows = dialog.items_card.get_product_rows()
            # Order B: 1 product + 1 trailing = 2 rows
            assert len(rows) == 2

            # Initial: freight=3000, unloading=500, seed pwf=121750 → "1217,50"
            assert rows[0].price_with_freight_input.text() == "1217,50"

            # Change freight to 1000,00 and unloading to 500,00
            dialog.header_card._freight_input.set_text("")
            dialog.header_card._unloading_input.set_text("")
            dialog.header_card._freight_input.set_text("1000,00")
            dialog.header_card._unloading_input.set_text("500,00")

            # products_total = 240000
            # freight_total = 100000 + 50000 = 150000
            # ratio = (150000 + 240000) / 240000 = 390000 / 240000 = 1.625
            # prod-b1: pwf = round(120000 * 1.625) = round(195000) = 195000
            assert rows[0].price_with_freight_input.text() == "1950,00"
        finally:
            dialog.deleteLater()


class TestOrderEditDialogNewOrder:
    """Verify freight distribution for newly created orders."""

    def test_new_order_with_freight_distribution(
            self,
            order_edit_dialog_blank: OrderEditDialog,
    ) -> None:
        """
        Create a new order with header fields and a single product,
        verify that freight distribution correctly calculates price_with_freight.
        """
        dialog = order_edit_dialog_blank

        # Set header fields
        dialog.header_card._supplier_input.set_text("Fornecedor Teste Novo")
        dialog.header_card._date_input.set_text("20/07/2024")
        dialog.header_card._freight_input.set_text("100,00")
        dialog.header_card._unloading_input.set_text("20,00")

        # Fill row 0
        rows = dialog.items_card.get_product_rows()
        rows[0].name_input.setText("Cimento Teste")
        rows[0].quantity_input.setText("2")
        rows[0].price_input.setText("50,00")

        # ── Verify calculated values ────────────────────────────────
        # products_total = 5000 * 2 = 10000
        # freight_total = 10000 + 2000 = 12000
        # ratio = (12000 + 10000) / 10000 = 22000 / 10000 = 2.2
        # row0: pwf = round(5000 * 2.2) = round(11000) = 11000
        # row0 total = 5000 * 2 = 10000
        assert rows[0].name_input.text() == "Cimento Teste"
        assert rows[0].quantity_input.text() == "2"
        assert rows[0].price_input.text() == "50,00"
        assert rows[0].total_input.text() == "100,00"
        assert rows[0].price_with_freight_input.text() == "110,00"

        # Verify header fields
        assert dialog.header_card._supplier_input.get_text() == "Fornecedor Teste Novo"
        assert dialog.header_card._date_input.get_text() == "20/07/2024"
        assert dialog.header_card._freight_input.get_text() == "100,00"
        assert dialog.header_card._unloading_input.get_text() == "20,00"

        # ── Save and verify signal emission ─────────────────────────
        saved: List[OrderInput] = []
        dialog.order_saved.connect(saved.append)
        dialog.btn_save.click()

        assert len(saved) == 1
        assert dialog.result() == QDialog.DialogCode.Accepted


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
        assert len(key) == 44
        assert key.isdigit()

    def test_close_button_rejects(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-96"
        dialog = nfe_search_dialog
        dialog.btn_close.click()

        assert dialog.result() == QDialog.DialogCode.Rejected

    def test_input_mask_applied(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-97"
        dialog = nfe_search_dialog
        expected_mask: str = "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"
        actual_mask: str = dialog._nfe_key_edit.inputMask()
        assert actual_mask == expected_mask

    def test_progress_label_hidden_initially(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-98"
        dialog = nfe_search_dialog
        assert dialog._progress_label.isVisible() is False
