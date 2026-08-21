# Implementation Plan: Widget Tests for OrderEditDialog

## Summary

This plan specifies widget tests (pytest-qt) for the `OrderEditDialog` component hierarchy — the main dialog, `OrderHeaderCard`, `OrderItemsCard`, `ProductRowWidget`, and `NfeSearchDialog`. Tests continue the TC numbering from TC-16 (existing order_edit_list tests end at TC-15). Tests follow the pattern established by `test_expense_edit_dialog.py`.

---

## A. Test File Structure

Three test files will be created, plus one new fixture file and modifications to `tests/conftest.py`:

| # | File (relative to project root) | Coverage | TC Range |
|---|--------------------------------|----------|----------|
| 1 | `tests/frontend/views/order_edit/test_order_header_card.py` | `OrderHeaderCard` — fields, data loading, validation, currency parsing | TC-16 through TC-21 |
| 2 | `tests/frontend/views/order_edit/test_order_items_card.py` | `OrderItemsCard` — data loading, add/delete row, auto-add, total, validation, freight distribution button state | TC-22 through TC-34 |
| 3 | `tests/frontend/views/order_edit/test_order_edit_dialog.py` | `OrderEditDialog` (main), `ProductRowWidget`, `NfeSearchDialog` — init paths, save flow, validation, close, row widget, NFe key validation, XML import | TC-35 through TC-53 |

---

## B. New Fixture File

### `tests/fixtures/order_edit_dialog.py`

Create this file. It provides four fixtures following the `expenses_edit.py` pattern:

```python
# tests/fixtures/order_edit_dialog_fixture.py

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from di.injector_module import get_injector
from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog

from backend.services.xml_import_service import XmlImportService
from models.order import Order


_NFE_XML_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "nfe.xml"


@pytest.fixture
def order_edit_dialog_existing(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[OrderEditDialog, None, None]:
    """Create an OrderEditDialog for editing existing Order A (seeded in DB)."""
    injector = get_injector()
    factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
    dialog = factory(parent=None, order_id="order-a", order=None)
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def order_edit_dialog_blank(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[OrderEditDialog, None, None]:
    """Create a blank OrderEditDialog (no order_id, no order — new order path)."""
    injector = get_injector()
    factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
    dialog = factory(parent=None, order_id=None, order=None)
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def order_edit_dialog_xml_import(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[OrderEditDialog, None, None]:
    """Create an OrderEditDialog pre-populated from the real nfe.xml.

    Reads ``docs/nfe.xml``, calls ``XmlImportService.parse_xml_file()``
    to produce a real ``Order`` dataclass (with correct product data,
    IPI, ICMS-ST from the XML).  No SEFAZ network calls are made.
    """
    injector = get_injector()
    factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)

    service = XmlImportService()
    result = service.parse_xml_file(str(_NFE_XML_PATH))
    # The nfe.xml contains a single order
    order: Order = result.orders[0]

    dialog = factory(parent=None, order_id=None, order=order)
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def product_row_widget(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator["ProductRowWidget", None, None]:
    """Create a standalone ProductRowWidget for unit testing the row widget.

    Uses the OrderEditDialog's items_card to create a row so that
    the parent hierarchy is correct.
    """
    from frontend.views.order_edit.product_row_widget import ProductRowWidget

    injector = get_injector()
    factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
    dialog = factory(parent=None, order_id=None, order=None)
    qtbot.addWidget(dialog)
    dialog.show()

    row: ProductRowWidget = dialog.items_card.add_row()
    qtbot.addWidget(row)
    yield row

    row.deleteLater()
    dialog.deleteLater()


@pytest.fixture
def nfe_search_dialog(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator["NfeSearchDialog", None, None]:
    """Create an NfeSearchDialog wired to the test database."""
    from frontend.factories.nfe_search_dialog_factory import NfeSearchDialogFactory
    from frontend.views.order_edit.nfe_search_dialog import NfeSearchDialog

    injector = get_injector()
    factory: NfeSearchDialogFactory = injector.get(NfeSearchDialogFactory)
    dialog = factory(parent=None)
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()
```

---

## C. Files to Modify

### `tests/conftest.py`

Add imports and exports for the new fixtures:

```python
# Add these lines near the other imports (after the expense edit imports):

# Order edit fixtures
from tests.fixtures.order_edit_dialog_fixture import (
    order_edit_dialog_existing,
    order_edit_dialog_blank,
    order_edit_dialog_xml_import,
    product_row_widget,
    nfe_search_dialog,
)

# Add to __all__:
"order_edit_dialog_existing",
"order_edit_dialog_blank",
"order_edit_dialog_xml_import",
"product_row_widget",
"nfe_search_dialog",
```

---

## D. Test File 1: `tests/frontend/views/order_edit/test_order_header_card.py`

**TC Range:** TC-16 through TC-21

### Fixture

- `order_edit_dialog_existing` — provides a dialog loaded with Order A data.

### Test Classes and Tests

#### `TestOrderHeaderCardFieldDisplay` (TC-16)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_supplier_field_displays_correct_value` | Verify supplier text loaded from Order A | `dialog.header_card._supplier_input.get_text() == "Cimento Portland"` |
| `test_date_field_displays_in_br_format` | Verify date converted from ISO to BR | `dialog.header_card._date_input.get_text() == "10/07/2024"` |
| `test_freight_field_displays_currency` | Verify freight in cents → display format | `dialog.header_card._freight_input.get_text() == "50,00"` (Order A freight=5000 cents) |
| `test_unloading_field_displays_currency` | Verify unloading in cents → display format | `dialog.header_card._unloading_input.get_text() == "10,00"` (Order A unloading=1000 cents) |
| `test_freight_field_empty_when_zero` | If freight is 0 in Order, field should be empty | Create Order with freight=0, verify `get_text() == ""` |

#### `TestOrderHeaderCardDataLoading` (TC-17)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_set_order_data_loads_all_fields` | Call `set_order_data()` with a different Order and verify all fields | Load Order B data: supplier="Areia Premium LTDA", date="15/07/2024", freight="30,00", unloading="5,00" |
| `test_set_order_data_emits_order_changed` | Verify `order_changed` signal fires on data load | Connect signal via list append, verify list has 1 item |
| `test_freight_zero_not_set` | When freight=0, the field should remain empty (not "0,00") | Create Order with freight=0, assert `_freight_input.get_text() == ""` |
| `test_unloading_zero_not_set` | Same for unloading | Same assertion pattern |

#### `TestOrderHeaderCardValidation` (TC-18, TC-19)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_validate_missing_supplier` | Clear supplier, validate | `(False, ["Campo obrigatório"])` — supplier error |
| `test_validate_valid_data` | With all fields filled (from Order A), validate | `(True, [])` |
| `test_validate_invalid_date` | Set date to "32/13/2024" (invalid), validate | `(False, ["Data inválida"])` |

#### `TestOrderHeaderCardCurrencyParsing` (TC-20, TC-21)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_get_freight_cents_parses_currency` | Set freight to "123,45", call `get_freight_cents()` | `== 12345` |
| `test_get_unloading_cents_parses_currency` | Set unloading to "1.000,00", call `get_unloading_cents()` | `== 100000` |
| `test_get_freight_cents_handles_empty` | Empty string → 0 | `== 0` |

---

## E. Test File 2: `tests/frontend/views/order_edit/test_order_items_card.py`

**TC Range:** TC-22 through TC-34

### Fixture

- `order_edit_dialog_existing` — dialog with Order A (2 products + trailing empty row = 3 rows)
- `order_edit_dialog_blank` — dialog with 1 empty row

### Test Classes and Tests

#### `TestOrderItemsCardDataLoading` (TC-22)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_loads_order_a_products` | Verify Order A products loaded into rows | `len(rows) == 3` (2 products + 1 trailing). Row 0: name="Cimento CP-II 50kg", qty="1", price="250,00", total="250,00". Row 1: name="Cimento CP-II 1kg", qty="1", price="5,00", total="5,00". Row 2: `is_empty() == True` |
| `test_loads_order_b_products` | Verify Order B (1 product) loaded | `len(rows) == 2` (1 product + 1 trailing). Row 0: name="Areia média", qty="2", price="150,00", total="300,00" |
| `test_total_label_shows_correct_total` | Verify footer total label | `dialog.items_card._products_total_label.text() == "Total dos produtos: 255,00"` (25000+500=25500 cents) |
| `test_set_order_data_emits_order_changed` | Signal fires on data load | List append, `len == 1` |

#### `TestOrderItemsCardAddRow` (TC-23)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_add_row_increases_row_count` | Call `add_row()`, verify row count | `len(rows) == 4` (from 3) |
| `test_add_row_emits_row_added_signal` | Verify `row_added` signal | List append, `len == 1` |
| `test_add_row_creates_empty_row` | New row should be empty | `new_row.is_empty() == True` |

#### `TestOrderItemsCardDeleteRow` (TC-24)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_delete_row_via_button_click` | Click delete on row 0 | `len(rows) == 2` (from 3). Last row (trailing) delete button disabled |
| `test_delete_button_state_after_delete` | Verify delete button states | Last row: `isEnabled() == False`. Remaining non-last rows: `isEnabled() == True` |
| `test_delete_row_via_signal` | Simulate `delete_pressed` signal | Same effect as button click |

#### `TestOrderItemsCardAutoAddRow` (TC-25)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_auto_add_when_trailing_row_filled` | Fill trailing row's name+qty+price, wait | New row auto-added, `len(rows) == 4` |
| `test_auto_add_preserves_filled_row_data` | After auto-add, verify original row still has data | Row data unchanged |
| `test_auto_add_new_row_is_empty` | The newly added trailing row is empty | `is_empty() == True` |

#### `TestOrderItemsCardTotalCalculation` (TC-26, TC-27)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_total_updates_on_price_change` | Change price in a row, verify total | Change row 0 price to "300,00" → total = 30000+500 = 30500 → "305,00" |
| `test_total_updates_on_quantity_change` | Change quantity, verify total | Change row 0 qty to "2" → total = 50000+500 = 50500 → "505,00" |
| `test_total_excludes_trailing_empty_row` | Verify trailing row not counted | Total matches sum of non-empty rows only |
| `test_total_is_zero_with_empty_rows` | Blank dialog total | `dialog.items_card._products_total_label.text() == "Total dos produtos: 0,00"` |

#### `TestOrderItemsCardProductsList` (TC-28)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_get_products_list_excludes_trailing_row` | Call `get_products_list("test-order")` | Returns 2 items for Order A (not 3) |
| `test_get_products_list_returns_correct_data` | Verify ProductInput fields | `products[0].name == "Cimento CP-II 50kg"`, `quantity == 1`, `price == 25000`, `total == 25000`, `order_id == "test-order"`, `item_ordinal == 0` |
| `test_get_products_list_after_add_row` | After auto-add, list still excludes trailing | Same as above |

#### `TestOrderItemsCardValidation` (TC-29 through TC-34)

| Test | TC | Description | Assertions |
|------|-----|-------------|------------|
| `test_partial_row_name_only` | TC-29 | Fill only name in a row, validate with `show_errors=True` | `(False, ["Produto 1: Nome do produto obrigatório quando outros campos estão preenchidos."])`. `_error.isVisible() == True` |
| `test_partial_row_quantity_only` | TC-30 | Fill only quantity | `(False, ["Produto 1: Quantidade do produto obrigatória quando outros campos estão preenchidos."])` |
| `test_partial_row_price_only` | TC-31 | Fill only price | `(False, ["Produto 1: Preço do produto obrigatório quando outros campos estão preenchidos."])` |
| `test_all_valid_rows_pass` | TC-32 | Order A rows are all valid | `(True, [])` |
| `test_all_empty_rows_pass` | TC-33 | All rows empty (blank dialog) | `(True, [])` |
| `test_mixed_valid_invalid_rows` | TC-34 | One valid, one invalid — combined errors | `(False, ["Produto 1: ...", "Produto 2: ..."])`. Error count matches invalid rows |

---

## F. Test File 3: `tests/frontend/views/order_edit/test_order_edit_dialog.py`

**TC Range:** TC-35 through TC-53

### Fixtures

- `order_edit_dialog_existing` — Order A from DB
- `order_edit_dialog_blank` — new blank dialog
- `order_edit_dialog_xml_import` — pre-populated Order (XML path)
- `product_row_widget` — standalone ProductRowWidget
- `nfe_search_dialog` — NfeSearchDialog

### Test Classes and Tests

#### `TestOrderEditDialogInit` (TC-35, TC-36, TC-37)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_init_with_existing_order_populates_fields` | Order A loaded from DB | `header_card._supplier_input.get_text() == "Cimento Portland"`, `_date_input.get_text() == "10/07/2024"`, freight="50,00", unloading="10,00". Items: 2 product rows + 1 trailing. `dialog.windowTitle() == "Editar Pedido"` |
| `test_init_with_existing_order_loads_products` | Verify products loaded | `len(rows) == 3`. Row 0: name="Cimento CP-II 50kg", qty="1", price="250,00", total="250,00". Row 1: name="Cimento CP-II 1kg", qty="1", price="5,00", total="5,00" |
| `test_init_with_blank_order_has_one_empty_row` | Blank path | `len(rows) == 1`. `rows[0].is_empty() == True`. `dialog.windowTitle() == "Novo Pedido"` |
| `test_init_with_xml_import_populates_fields` | XML import path (real `docs/nfe.xml`) | `header_card._supplier_input.get_text() == "O.V.D. IMPORTADORA E DISTRIBUIDORA LTDA"` (emit.xFant from XML), `_date_input.get_text() == "02/07/2026"` (from `dhEmi`), freight="0,00", unloading="0,00". Items: 1 product row (CORDA MULTIF TRANC 6MMX180M BCA VONDER) + 1 trailing. `dialog.windowTitle() == "Novo Pedido"`. `_imported_order` attribute exists. `nfe_key` matches the 44-digit key from XML. |

#### `TestOrderEditDialogSave` (TC-38, TC-39)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_save_valid_edited_order` | Edit a field, save, verify success | Edit supplier to "Fornecedor Editado", save. `"Salvo com sucesso!" in message_label.text()`. `order_saved` signal emitted (list append, `len == 1`). `result() == QDialog.DialogCode.Accepted` |
| `test_save_emits_order_with_correct_data` | Verify the emitted OrderInput has edited data | Connect `order_saved.connect(saved.append)`. Edit supplier and a product. Save. `saved[0].supplier == "Fornecedor Editado"`. `len(saved[0].products) == 2` |
| `test_save_preserves_nfe_key_on_xml_import` | XML-imported order save preserves nfe_key | Load XML dialog (from `docs/nfe.xml`). Save. `saved[0].nfe_key == "2260776635689001326550020004218041000629450"` (the 44-digit key extracted from the XML's `infNFe Id` attribute, without the `NFe` prefix). |
| `test_save_invalid_order_does_not_save` | Leave supplier blank, save | `"Salvo com sucesso!" NOT in message`. Signal NOT emitted. `result() != QDialog.DialogCode.Accepted` |

#### `TestOrderEditDialogValidation` (TC-40, TC-41)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_save_with_header_validation_errors` | Clear supplier, save | Header validation fails. No save, no accept. `header_card._supplier_input._was_validated == True` (TextField marks validated) |
| `test_save_with_items_validation_errors` | Fill only name in a product row, save | Items validation fails. No save, no accept. `_error` visible on the invalid row |
| `test_save_with_both_header_and_items_errors` | Both header and items invalid | Only header errors shown (items errors not shown because header fails first) |

#### `TestOrderEditDialogClose` (TC-42)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_close_button_rejects` | Click Fechar | `result() == QDialog.DialogCode.Rejected` |
| `test_close_emits_closed_signal` | Verify `closed` signal | List append, `len == 1` |

#### `TestOrderEditDialogMessageLabel` (TC-43, TC-44)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_success_message_styled_correctly` | After successful save, verify message style | `message_label.text() == "Salvo com sucesso!"`. `message_label.styleSheet()` contains `background-color: #d4edda` |
| `test_error_message_styled_correctly` | After failed save, verify message style | `message_label.text() == "Erro ao salvar pedido."`. Style contains `background-color: #f8d7da` |
| `test_message_label_clears_after_timeout` | After 5 seconds, message should clear | Patch `QTimer.singleShot` to call the callback immediately, then verify `message_label.text() == ""` |

#### `TestProductRowWidget` (TC-45 through TC-50)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_auto_calculation_price_times_quantity` | Set price="100,00", qty="3" → total="300,00" | `row.total_input.text() == "300,00"` |
| `test_auto_calculation_with_empty_price` | qty="5", price="" → total="0,00" | `row.total_input.text() == "0,00"` |
| `test_auto_calculation_with_empty_quantity` | price="50,00", qty="" → total="0,00" | `row.total_input.text() == "0,00"` |
| `test_auto_calculation_both_empty` | Both empty → total="0,00" | `row.total_input.text() == "0,00"` |
| `test_is_empty_fully_empty` | Fresh row | `row.is_empty() == True` |
| `test_is_empty_partially_filled` | Name="Teste" only | `row.is_empty() == False` |
| `test_is_empty_all_fields_filled` | All fields filled | `row.is_empty() == False` |
| `test_get_product_data_returns_correct_data` | Fill name="Cimento", qty="2", price="25,00" | `ProductInput(name="Cimento", quantity=2, price=2500, total=5000, order_id="test-order", item_ordinal=0)` |
| `test_validate_required_if_filled_all_three` | Name+qty+price filled → valid | `(True, [])`, `_error.isVisible() == False` |
| `test_validate_required_if_filled_name_only` | Name only → invalid | `(False, ["Nome do produto obrigatório quando outros campos estão preenchidos."])`, `_error.isVisible() == True` |
| `test_validate_required_if_filled_qty_only` | Qty only → invalid | `(False, ["Quantidade do produto obrigatória quando outros campos estão preenchidos."])` |
| `test_validate_required_if_filled_price_only` | Price only → invalid | `(False, ["Preço do produto obrigatório quando outros campos estão preenchidos."])` |
| `test_validate_required_if_filled_name_plus_qty` | Name+qty, no price → invalid | `(False, ["Preço do produto obrigatório quando outros campos estão preenchidos."])` |
| `test_validate_required_if_filled_all_empty` | All empty → valid | `(True, [])`, `_error.isVisible() == False` |
| `test_warning_icon_displayed_with_warnings` | Call `set_warnings(["IPI diferenciado"])` | `warning_icon.pixmap() is not None` (has a pixmap set) |
| `test_warning_icon_hidden_without_warnings` | Call `set_warnings([])` | `warning_icon.pixmap() is None` |
| `test_error_label_hidden_when_valid` | Valid row, call validate | `_error.isVisible() == False` |
| `test_error_label_visible_when_invalid` | Invalid row, validate with `show_errors=True` | `_error.isVisible() == True` |
| `test_row_changed_signal_emitted` | Type into name field | `row_changed` signal fires (list append, `len == 1`) |
| `test_delete_pressed_signal_emitted` | Click delete button | `delete_pressed` signal fires |

#### `TestProductRowWidgetPreFilled` (TC-51)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_row_pre_filled_with_product_data` | Create row with `Product` dataclass | name_input="Cimento CP-II 50kg", qty="1", price="250,00", total="250,00" |

#### `TestNfeSearchDialog` (TC-52)

| Test | Description | Assertions |
|------|-------------|------------|
| `test_invalid_key_too_short` | Enter "12345" → click Consultar | `QMessageBox.warning` shown (verify via `qtbot.addWidget` or mock). Dialog stays open (not accepted) |
| `test_invalid_key_non_digits` | Enter "abcdefghijklmnop..." (44 chars, non-digit) → click Consultar | Warning shown. Dialog stays open |
| `test_valid_key_44_digits_enables_search` | Enter 44 zeros (mask fills them) → button should be enabled for clicking | `_nfe_key_edit.text()` has 44 digits. `btn_search.isEnabled() == True` |
| `test_close_button_rejects` | Click Fechar | `result() == QDialog.DialogCode.Rejected` |
| `test_input_mask_applied` | Verify input mask | `_nfe_key_edit.inputMask() == "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"` |
| `test_progress_label_hidden_initially` | Dialog just opened | `_progress_label.isVisible() == False` |

---

## G. Implementation Order

The suggested implementation sequence minimizes merge conflicts and maintains a working state at each step:

1. **Create `tests/fixtures/order_edit_dialog.py`** — all fixtures needed by subsequent tests
2. **Modify `tests/conftest.py`** — import and export new fixtures
3. **Create `tests/frontend/views/order_edit/` directory** — new test subdirectory
4. **Create `tests/frontend/views/order_edit/test_order_header_card.py`** — simplest component, no dialog-level dependencies
5. **Create `tests/frontend/views/order_edit/test_order_items_card.py`** — depends on fixtures from step 1
6. **Create `tests/frontend/views/order_edit/test_order_edit_dialog.py`** — most complex, depends on all fixtures
7. **Run `pytest`** — verify all tests pass

---

## H. Mocking Strategy

### NFe XML Import — Real File, No SEFAZ Calls

The `docs/nfe.xml` file is a complete, valid NFe XML (v4.00) from a real transaction. The fixture `order_edit_dialog_xml_import` reads this file directly via `XmlImportService.parse_xml_file()` — **no SEFAZ network calls are made**. The XML contains:

- **Emitter:** O.V.D. IMPORTADORA E DISTRIBUIDORA LTDA (CNPJ 76635689001326)
- **NFe key:** 2260776635689001326550020004218041000629450 (44 digits)
- **Date:** 2026-07-02
- **1 product:** CORDA MULTIF TRANC 6MMX180M BCA VONDER (NCM 56074900, CFOP 5102)
- **ICMS:** ICMS20 with IPI and ICMS-ST included in base price

This approach tests the real XML parsing pipeline (including IPI/ICMS-ST price adjustments) without any network dependencies.

### NfeSearchDialog — Worker Mocking

For `test_order_edit_dialog.py` tests that involve the NFE search worker:

- **Do NOT make real SEFAZ calls** in any test. Only test key validation and UI state.
- If tests need to verify worker start behavior, use `unittest.mock.patch` on `NfeSearchDialog._start_worker` to prevent actual thread creation.
- The NfeSearchDialog tests only verify: key format validation (too short, non-digits, valid 44 digits), input mask, progress label visibility, and close button.

### OrderBridge.save_single_order — Real DB

The `save_single_order` bridge call goes through the real test database (via patched `temp_engine`). No mocking needed — the test DB seeded by `temp_engine` supports save operations. The fixture's DI already patches `get_engine` to point to the temp engine.

### QTimer.singleShot — Message Auto-Clear

For testing the 5-second message auto-clear, use:
```python
from unittest.mock import patch, MagicMock
with patch('PySide6.QtCore.QTimer.singleShot') as mock_timer:
    # Call the callback directly to simulate timer expiry
    mock_timer.call_args[0][1]()  # second arg is the callback
    assert dialog.message_label.text() == ""
```

---

## I. Risks and Considerations

1. **Signal timing:** Qt signals in tests may fire after `qtbot.wait()` is called. Always use `qtbot.wait(100)` after user-like interactions (typing, clicking) to allow signal chains to resolve.

2. **Dialog result state:** After `dialog.show()`, `result()` returns `QDialog.DialogCode.Unspecified` until `accept()` or `reject()` is called. Tests must trigger the action (click button) before checking `result()`.

3. **DeleteLater cleanup:** The `deleteLater()` call in fixtures means widgets may not be immediately destroyed. The `qtbot` context manager handles this, but tests should not access widgets after the fixture yields.

4. **Currency parsing edge cases:** `parse_currency_to_cents` handles both `,` and `.` as decimal separators. Tests should cover both formats.

5. **Date input mask:** The date field uses `99/99/9999` mask. Setting text programmatically via `setText()` bypasses the mask — this is the correct approach for tests. The `DateValidator` checks semantic validity separately.

6. **Auto-add row timing:** The auto-add behavior is triggered by `_on_row_changed` which fires on `row_changed` signal, which fires on `textChanged`. In tests, use `qtbot.wait(100)` after setting text to allow the signal chain to complete before checking row count.

7. **No __init__.py files:** The project uses namespace packages with no `__init__.py`. Test files should import using the same path conventions as the source (e.g., `from frontend.views.order_edit.product_row_widget import ProductRowWidget`).

8. **Portuguese strings:** All UI text, error messages, and labels are in Brazilian Portuguese. Assertions must match exact strings from the source code.

---

## J. Test Count Summary

| Test File | Test Classes | Test Functions | TC Range |
|-----------|-------------|----------------|----------|
| `test_order_header_card.py` | 4 classes | 15 tests | TC-16 through TC-21 |
| `test_order_items_card.py` | 7 classes | 26 tests | TC-22 through TC-34 |
| `test_order_edit_dialog.py` | 8 classes | 43 tests | TC-35 through TC-53 |
| **Total** | **19 classes** | **84 tests** | **TC-16 through TC-53** |

Removed: `TestOrderHeaderCardClear` (clear tests), `TestOrderHeaderCardDateFormat` (date mask/placeholder), `TestOrderHeaderCardSignals` (header card signals), and `TestOrderItemsCardFreightDistributionButton` (button state implicitly covered in dialog save flow).
