from __future__ import annotations

from typing import List
from unittest.mock import patch

from PySide6.QtWidgets import QDialog, QMessageBox
from pytestqt.qtbot import QtBot

from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory
from di.injector_module import get_injector
from tests.fixtures.order_edit_dialog_fixture import (
    order_edit_dialog_existing,
    order_edit_dialog_blank,
    order_edit_dialog_xml_import,
)
from models.input import OrderInput


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

        assert rows[0]._name_input.text() == "Cimento CP-II 50kg"
        assert rows[0]._quantity_input.text() == "1"
        assert rows[0]._price_input.text() == "250,00"
        assert rows[0]._total_with_freight_input.text() == "250,00"

        assert rows[1]._name_input.text() == "Cimento CP-II 1kg"
        assert rows[1]._quantity_input.text() == "1"
        assert rows[1]._price_input.text() == "5,00"
        assert rows[1]._total_with_freight_input.text() == "5,00"

        # price_with_freight assertions — loaded from DB via seed data
        assert rows[0]._price_with_freight_input.text() == "308,82"
        assert rows[1]._price_with_freight_input.text() == "6,18"

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
        rows[0]._price_input.setText("300,00")

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
            if row._quantity_input.text() == "0":
                row._quantity_input.setText("1")
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
        rows[-1]._name_input.setText("Produto incompleto")

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
        rows[-1]._name_input.setText("Produto incompleto")

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
        assert rows[0]._price_with_freight_input.text() == "308,82"
        assert rows[1]._price_with_freight_input.text() == "6,18"

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
        assert rows[0]._price_with_freight_input.text() == "495,10"
        assert rows[1]._price_with_freight_input.text() == "9,90"

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
        assert rows[0]._price_with_freight_input.text() == "250,00"
        # Row 1: price = 500 cents → "5,00"
        assert rows[1]._price_with_freight_input.text() == "5,00"

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
            assert rows[0]._price_with_freight_input.text() == "1217,50"

            # Change freight to 1000,00 and unloading to 500,00
            dialog.header_card._freight_input.set_text("")
            dialog.header_card._unloading_input.set_text("")
            dialog.header_card._freight_input.set_text("1000,00")
            dialog.header_card._unloading_input.set_text("500,00")

            # products_total = 240000
            # freight_total = 100000 + 50000 = 150000
            # ratio = (150000 + 240000) / 240000 = 390000 / 240000 = 1.625
            # prod-b1: pwf = round(120000 * 1.625) = round(195000) = 195000
            assert rows[0]._price_with_freight_input.text() == "1950,00"
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
        rows[0]._name_input.setText("Cimento Teste")
        rows[0]._quantity_input.setText("2")
        rows[0]._price_input.setText("50,00")

        # ── Verify calculated values ────────────────────────────────
        # products_total = 5000 * 2 = 10000
        # freight_total = 10000 + 2000 = 12000
        # ratio = (12000 + 10000) / 10000 = 22000 / 10000 = 2.2
        # row0: pwf = round(5000 * 2.2) = round(11000) = 11000
        # row0 total = 5000 * 2 = 10000
        assert rows[0]._name_input.text() == "Cimento Teste"
        assert rows[0]._quantity_input.text() == "2"
        assert rows[0]._price_input.text() == "50,00"
        assert rows[0]._total_with_freight_input.text() == "100,00"
        assert rows[0]._price_with_freight_input.text() == "110,00"

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
