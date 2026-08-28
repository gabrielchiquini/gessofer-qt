from __future__ import annotations

from typing import List

from PySide6.QtWidgets import QDialog

from models.order import Order
from di.injector_module import get_injector
from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory
from tests.fixtures.order_edit_dialog_fixture import order_edit_dialog_existing  # noqa: F401
from tests.fixtures.seed_data import ORDERS_DATA
from backend.utils.currency import cents_to_input
from backend.utils.date import datetime_to_br_date


class TestOrderHeaderCardFieldDisplay:
    """TC-16 through TC-19: Verify field display from Order A data."""

    def test_supplier_field_displays_correct_value(
        self,
        order_edit_dialog_existing: QDialog,
    ) -> None:
        tc_id: str = "TC-16"
        dialog = order_edit_dialog_existing
        actual: str = dialog.header_card._supplier_input.get_text()
        assert actual == ORDERS_DATA[0].supplier, f"{tc_id}: expected '{ORDERS_DATA[0].supplier}', got {actual!r}"

    def test_date_field_displays_in_br_format(
        self,
        order_edit_dialog_existing: QDialog,
    ) -> None:
        tc_id: str = "TC-17"
        dialog = order_edit_dialog_existing
        actual: str = dialog.header_card._date_input.get_text()
        assert actual == datetime_to_br_date(ORDERS_DATA[0].date), f"{tc_id}: expected '{datetime_to_br_date(ORDERS_DATA[0].date)}', got {actual!r}"

    def test_freight_field_displays_currency(
        self,
        order_edit_dialog_existing: QDialog,
    ) -> None:
        tc_id: str = "TC-18"
        dialog = order_edit_dialog_existing
        actual: str = dialog.header_card._freight_input.get_text()
        assert actual == cents_to_input(ORDERS_DATA[0].freight), f"{tc_id}: expected '{cents_to_input(ORDERS_DATA[0].freight)}', got {actual!r}"

    def test_unloading_field_displays_currency(
        self,
        order_edit_dialog_existing: QDialog,
    ) -> None:
        tc_id: str = "TC-19"
        dialog = order_edit_dialog_existing
        actual: str = dialog.header_card._unloading_input.get_text()
        assert actual == cents_to_input(ORDERS_DATA[0].unloading), f"{tc_id}: expected '{cents_to_input(ORDERS_DATA[0].unloading)}', got {actual!r}"


class TestOrderHeaderCardDataLoading:
    """TC-20 through TC-23: Verify set_order_data loading and signals."""

    def test_set_order_data_loads_all_fields(
        self,
        temp_engine: object,
        qtbot: object,
    ) -> None:
        tc_id: str = "TC-20"
        injector = get_injector()
        factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
        dialog: QDialog = factory(parent=None, order_id="order-b", order=None)
        qtbot.addWidget(dialog)
        dialog.show()

        try:
            assert dialog.header_card._supplier_input.get_text() == ORDERS_DATA[1].supplier, \
                f"{tc_id}: supplier mismatch"
            assert dialog.header_card._date_input.get_text() == datetime_to_br_date(ORDERS_DATA[1].date), \
                f"{tc_id}: date mismatch"
            assert dialog.header_card._freight_input.get_text() == cents_to_input(ORDERS_DATA[1].freight), \
                f"{tc_id}: freight mismatch"
            assert dialog.header_card._unloading_input.get_text() == cents_to_input(ORDERS_DATA[1].unloading), \
                f"{tc_id}: unloading mismatch"
        finally:
            dialog.deleteLater()

    def test_set_order_data_emits_order_changed(
        self,
        order_edit_dialog_existing: QDialog,
    ) -> None:
        tc_id: str = "TC-21"
        dialog = order_edit_dialog_existing
        emitted: List[object] = []
        dialog.header_card.order_changed.connect(lambda: emitted.append(True))
        dialog.header_card._supplier_input.set_text("Novo Fornecedor")
        assert len(emitted) >= 1, f"{tc_id}: order_changed not emitted"

    def test_freight_zero_not_set(
        self,
        temp_engine: object,
        qtbot: object,
    ) -> None:
        tc_id: str = "TC-22"
        injector = get_injector()
        factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)

        order: Order = Order(
            id="zero-freight-order",
            date="2024-08-01",
            supplier="Test Supplier",
            nfe_key="00000000000000",
            freight=0,
            unloading=0,
            products=[],
        )
        dialog: QDialog = factory(parent=None, order_id=None, order=order)
        qtbot.addWidget(dialog)
        dialog.show()

        try:
            freight_text: str = dialog.header_card._freight_input.get_text()
            assert freight_text == "", \
                f"{tc_id}: expected empty freight field, got {freight_text!r}"
        finally:
            dialog.deleteLater()

    def test_unloading_zero_not_set(
        self,
        temp_engine: object,
        qtbot: object,
    ) -> None:
        tc_id: str = "TC-23"
        injector = get_injector()
        factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)

        order: Order = Order(
            id="zero-unloading-order",
            date="2024-08-01",
            supplier="Test Supplier",
            nfe_key="00000000000000",
            freight=1000,
            unloading=0,
            products=[],
        )
        dialog: QDialog = factory(parent=None, order_id=None, order=order)
        qtbot.addWidget(dialog)
        dialog.show()

        try:
            unloading_text: str = dialog.header_card._unloading_input.get_text()
            assert unloading_text == "", \
                f"{tc_id}: expected empty unloading field, got {unloading_text!r}"
        finally:
            dialog.deleteLater()


class TestOrderHeaderCardValidation:
    """TC-24 through TC-26: Header validation tests."""

    def test_validate_missing_supplier(
        self,
        order_edit_dialog_existing: QDialog,
        qtbot: object,
    ) -> None:
        tc_id: str = "TC-24"
        dialog = order_edit_dialog_existing
        dialog.header_card._supplier_input.clear()
        qtbot.wait(100)

        valid, errors = dialog.header_card.validate()
        assert valid is False, f"{tc_id}: expected invalid"
        assert "Campo obrigatório" in errors, \
            f"{tc_id}: expected 'Campo obrigatório' in {errors}"

    def test_validate_valid_data(
        self,
        order_edit_dialog_existing: QDialog,
    ) -> None:
        tc_id: str = "TC-25"
        dialog = order_edit_dialog_existing
        valid, errors = dialog.header_card.validate()
        assert valid is True, f"{tc_id}: expected valid, got errors {errors}"
        assert errors == [], f"{tc_id}: expected no errors"

    def test_validate_invalid_date(
        self,
        order_edit_dialog_existing: QDialog,
        qtbot: object,
    ) -> None:
        tc_id: str = "TC-26"
        dialog = order_edit_dialog_existing
        dialog.header_card._date_input.set_text("32/13/2024")
        qtbot.wait(100)

        valid, errors = dialog.header_card.validate()
        assert valid is False, f"{tc_id}: expected invalid"
        assert any("Data" in e for e in errors), \
            f"{tc_id}: expected date error in {errors}"


class TestOrderHeaderCardCurrencyParsing:
    """TC-27 through TC-29: Currency parsing tests."""

    def test_get_freight_cents_parses_currency(
        self,
        order_edit_dialog_existing: QDialog,
        qtbot: object,
    ) -> None:
        tc_id: str = "TC-27"
        dialog = order_edit_dialog_existing
        dialog.header_card._freight_input.set_text("123,45")
        qtbot.wait(100)

        result: int = dialog.header_card.get_freight_cents()
        assert result == 12345, f"{tc_id}: expected 12345, got {result}"

    def test_get_unloading_cents_parses_currency(
        self,
        order_edit_dialog_existing: QDialog,
        qtbot: object,
    ) -> None:
        tc_id: str = "TC-28"
        dialog = order_edit_dialog_existing
        dialog.header_card._unloading_input.set_text("1000,00")
        qtbot.wait(100)

        result: int = dialog.header_card.get_unloading_cents()
        assert result == 100000, f"{tc_id}: expected 100000, got {result}"

    def test_get_freight_cents_handles_empty(
        self,
        order_edit_dialog_existing: QDialog,
        qtbot: object,
    ) -> None:
        tc_id: str = "TC-29"
        dialog = order_edit_dialog_existing
        dialog.header_card._freight_input.set_text("")
        qtbot.wait(100)

        result: int = dialog.header_card.get_freight_cents()
        assert result == 0, f"{tc_id}: expected 0, got {result}"
