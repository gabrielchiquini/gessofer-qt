# Implementation Plan: Tests for ProductListView

## Summary

This plan defines integration tests for `ProductListView` (`src/frontend/views/product_list.py`), the PySide6 widget that displays a paginated, filterable table of products. Tests will follow the existing `test_expense_list.py` patterns: class-based test classes with `TC-XX` docstrings, integration with the real DI container + temp database, and assertions on model data, UI elements, and button states.

## Correction Note

The original request stated TC-04 (month filter "07/2024") should return **5** products. After verifying the seeded data and the repository query (`Order.DATE DESC`), the correct count is **4**:
- Order E (2024-07-25): Cal hidratada 20kg
- Order B (2024-07-15): Areia média
- Order A (2024-07-10): Cimento CP-II 50kg, Cimento CP-II 1kg

All test counts in this plan use the verified values.

---

## Files to Create

### 1. `tests/fixtures/products.py`

**Purpose:** Provides the `product_list_widget` fixture for integration tests, mirroring the `expense_list_widget` pattern.

**Key contents:**
- A `@pytest.fixture` named `product_list_widget` that:
  - Depends on `temp_engine: Engine` and `qtbot: QtBot`
  - Imports `ProductBridge` from `bridge.product`
  - Gets the `ProductBridge` singleton from the DI injector
  - Creates `ProductListView(parent=None, product_bridge=product_bridge)`
  - Calls `qtbot.addWidget(widget)`, `widget.show()`
  - Yields the widget
  - Calls `widget.deleteLater()` on teardown
- Type hints on all functions and variables

**Dependencies:** `tests/fixtures/database.py` (via `temp_engine`), `bridge.product.ProductBridge`, `frontend.views.product_list.ProductListView`

### 2. `tests/frontend/views/test_product_list.py`

**Purpose:** Integration test suite for `ProductListView` covering TC-01 through TC-10.

**Key contents:**
- All test classes using the `product_list_widget` fixture (except TC-01 which follows the expense_list pattern of constructing the widget inline)
- Type hints on all methods
- Docstrings referencing the TC number
- Assertions on `widget._model`, `widget.filter_supplier`, `widget.filter_product`, `widget.filter_month`, `widget.page_label`, `widget.btn_prev`, `widget.btn_next`

---

## Files to Modify

### 1. `tests/conftest.py`

**Current state:** Re-exports fixtures from `tests/fixtures/database.py`, `tests/fixtures/orders.py`, `tests/fixtures/expenses.py`, and `tests/fixtures/expenses_edit.py`.

**Changes needed:**
- Add import: `from tests.fixtures.products import product_list_widget`
- Add `"product_list_widget"` to the `__all__` list

**Rationale:** Makes the fixture discoverable by pytest without requiring individual test files to import from `tests.fixtures.products` directly.

---

## Test Cases

### TC-01: Initial Load

**Class:** `TestProductListInitialLoad`

**Approach:** Construct widget inline (like TC-01 in `test_expense_list.py`) — get DI injector, resolve `ProductBridge`, create `ProductListView`, add to `qtbot`, show.

**Assertions:**
- `widget.scroll.isVisible()` is `True`
- `widget._model.rowCount()` is `7` (all seeded products loaded via `clear_filters()` in `__init__`)
- `widget.page_label.text()` is `"Página 1 de 1"`
- `widget.btn_prev.isEnabled()` is `False` (only 1 page)
- `widget.btn_next.isEnabled()` is `False` (only 1 page)
- `widget.filter_supplier.text()` is `""` (empty)
- `widget.filter_product.text()` is `""` (empty)
- `widget.filter_month.text()` is `""` (empty)

**Rationale:** Verifies the widget initializes correctly with seeded data, pagination shows 1 page, and navigation buttons are disabled.

---

### TC-02: Supplier Filter

**Class:** `TestProductListSupplierFilter`

**Approach:** Use `product_list_widget` fixture. Type "Cimento" into `filter_supplier`, click `btn_search`.

**Expected results (4 products, DATE DESC order):**
1. 05/08/2024 | Cimento Portland | Cimento CP-I 50kg
2. 25/07/2024 | Cimento Portland | Cal hidratada 20kg
3. 10/07/2024 | Cimento Portland | Cimento CP-II 50kg
4. 10/07/2024 | Cimento Portland | Cimento CP-II 1kg

**Assertions:**
- `widget._model.rowCount()` is `4`
- `widget.page_label.text()` is `"Página 1 de 1"`
- `widget._model.item(0, 1).text()` is `"Cimento Portland"` (column 1 = Fornecedor)
- `widget._model.item(0, 2).text()` is `"Cimento CP-I 50kg"` (column 2 = Produto)
- `widget._model.item(3, 2).text()` is `"Cimento CP-II 1kg"` (last row)

**Rationale:** Verifies the supplier filter uses normalized LIKE matching on the `SUPPLIER_NORMALIZED` column. "Cimento" matches "Cimento Portland" but not "Areia Premium LTDA" or "Tijolo & Cia".

---

### TC-03: Product Name Filter

**Class:** `TestProductListProductNameFilter`

**Approach:** Use `product_list_widget` fixture. Type "Areia" into `filter_product`, click `btn_search`.

**Expected results (1 product):**
1. 15/07/2024 | Areia Premium LTDA | Areia média

**Assertions:**
- `widget._model.rowCount()` is `1`
- `widget._model.item(0, 1).text()` is `"Areia Premium LTDA"`
- `widget._model.item(0, 2).text()` is `"Areia média"`

**Rationale:** Verifies the product name filter uses normalized LIKE matching on `NAME_NORMALIZED`. "areia" matches "Areia média" (normalized: "areia media") but not "Cimento CP-II 50kg" etc.

---

### TC-04: Month Filter

**Class:** `TestProductListMonthFilter`

**Approach:** Use `product_list_widget` fixture. Type "07/2024" into `filter_month`, click `btn_search`.

**Expected results (4 products, DATE DESC order):**
1. 25/07/2024 | Cimento Portland | Cal hidratada 20kg
2. 15/07/2024 | Areia Premium LTDA | Areia média
3. 10/07/2024 | Cimento Portland | Cimento CP-II 50kg
4. 10/07/2024 | Cimento Portland | Cimento CP-II 1kg

**Assertions:**
- `widget._model.rowCount()` is `4`
- `widget._model.item(0, 0).text()` is `"25/07/2024"` (column 0 = Data)
- `widget._model.item(3, 0).text()` is `"10/07/2024"` (last row)
- Products from August (Order D, Order C) are excluded

**Rationale:** Verifies the month filter parses "MM/yyyy" and correctly filters by `Order.DATE` range.

---

### TC-05: Combined Filters

**Class:** `TestProductListCombinedFilters`

**Approach:** Use `product_list_widget` fixture. Type "Cimento" into `filter_supplier`, type "07/2024" into `filter_month`, click `btn_search`.

**Expected results (3 products, DATE DESC order):**
1. 25/07/2024 | Cimento Portland | Cal hidratada 20kg
2. 10/07/2024 | Cimento Portland | Cimento CP-II 50kg
3. 10/07/2024 | Cimento Portland | Cimento CP-II 1kg

**Assertions:**
- `widget._model.rowCount()` is `3`
- All rows have `widget._model.item(row, 1).text()` == `"Cimento Portland"`
- All rows have `widget._model.item(row, 0).text()` ending with "/07/2024"

**Rationale:** Verifies both filters work together with AND logic.

---

### TC-06: Display Data Correctness

**Class:** `TestProductListDisplayCorrectness`

**Approach:** Use `product_list_widget` fixture. Use `btn_search` with no filters (shows all 7 products). Verify every cell in the table.

**Expected data (DATE DESC order):**

| Row | Data (col 0) | Fornecedor (col 1) | Produto (col 2) | Preço (col 3) | Total (col 4) |
|-----|-------------|-------------------|-----------------|---------------|---------------|
| 0 | 20/08/2024 | Tijolo & Cia | Tijolo cerâmico 8 furos | 12,00 | 240,00 |
| 1 | 05/08/2024 | Cimento Portland | Cimento CP-I 50kg | 220,00 | 220,00 |
| 2 | 25/07/2024 | Cimento Portland | Cal hidratada 20kg | 80,00 | 160,00 |
| 3 | 15/07/2024 | Areia Premium LTDA | Areia média | 150,00 | 300,00 |
| 4 | 10/07/2024 | Cimento Portland | Cimento CP-II 50kg | 250,00 | 250,00 |
| 5 | 10/07/2024 | Cimento Portland | Cimento CP-II 1kg | 5,00 | 5,00 |

**Assertions:**
- `widget._model.rowCount()` is `7`
- For each row `r`, verify all 5 columns match the table above
- Date format: always `dd/MM/yyyy` (2 digits day, 2 digits month, 4 digits year)
- Price format: Brazilian currency with comma decimal, dot thousands — e.g., `"12,00"`, `"220,00"`, `"150,00"`, `"250,00"`, `"5,00"`
- Total format: same Brazilian currency format — e.g., `"240,00"`, `"300,00"`, `"160,00"`

**Rationale:** Comprehensive cell-by-cell verification of the data transformation pipeline: ORM → bridge DTO → formatted strings → QStandardItemModel.

---

### TC-07: Empty State

**Class:** `TestProductListEmptyState`

**Approach:** Use `product_list_widget` fixture. Type "01/2023" into `filter_month` (month with no seeded data), click `btn_search`.

**Assertions:**
- `widget._model.rowCount()` is `0`
- `widget.page_label.text()` is `"Página 1 de 1"`
- `widget.btn_prev.isEnabled()` is `False`
- `widget.btn_next.isEnabled()` is `False`
- `widget.scroll` is still visible (the widget does not hide the scroll on empty results — only on exceptions)

**Rationale:** Verifies graceful handling of zero-results queries.

---

### TC-08: Pagination UI

**Class:** `TestProductListPagination`

**Approach:** Use `product_list_widget` fixture. All 7 products fit on one page (PAGE_SIZE=50), so verify single-page behavior and boundary navigation.

**Assertions:**
- `widget._page_count` is `1`
- `widget._current_page` is `1`
- `widget.page_label.text()` is `"Página 1 de 1"`
- Calling `widget.go_previous()` does not raise and leaves `_current_page` at 1
- Calling `widget.go_next()` does not raise and leaves `_current_page` at 1
- Both `btn_prev.isEnabled()` and `btn_next.isEnabled()` are `False`

**Rationale:** Even though all data fits on one page, verify that pagination navigation methods handle boundary conditions gracefully (no index errors, no infinite loops).

---

### TC-09: Clear Filters

**Class:** `TestProductListClearFilters`

**Approach:** Use `product_list_widget` fixture. Apply a filter (e.g., supplier "Cimento"), verify reduced results, then call `clear_filters()`.

**Steps:**
1. Type "Cimento" into `filter_supplier`, click `btn_search` → 4 rows
2. Call `widget.clear_filters()`
3. Verify all filter fields are empty
4. Verify table reloaded with all 7 products
5. Verify pagination is `"Página 1 de 1"`

**Assertions:**
- After filter: `widget._model.rowCount()` is `4`
- After clear: `widget.filter_supplier.text()` is `""`
- After clear: `widget.filter_product.text()` is `""`
- After clear: `widget.filter_month.text()` is `""`
- After clear: `widget._model.rowCount()` is `7`
- After clear: `widget.page_label.text()` is `"Página 1 de 1"`

**Rationale:** Verifies that `clear_filters()` resets all state and re-fetches all data.

---

### TC-10: Enter Key Triggers Search

**Class:** `TestProductListEnterKeySearch`

**Approach:** Use `product_list_widget` fixture. Simulate pressing Enter in a filter field. The widget connects `returnPressed` signal on all three filter fields to `search()`.

**Steps:**
1. Type "Areia" into `filter_product`
2. Simulate `returnPressed` signal: `widget.filter_product.returnPressed.emit()`
3. Verify the table updated

**Assertions:**
- `widget._model.rowCount()` is `1` (only "Areia média")
- `widget._model.item(0, 2).text()` is `"Areia média"`

**Rationale:** Verifies the `returnPressed` signal connection on filter fields triggers the search method, providing keyboard accessibility.

---

## Implementation Details

### Fixture Pattern (`tests/fixtures/products.py`)

```python
# Exact pattern to follow (mirrors tests/fixtures/expenses.py):
@pytest.fixture
def product_list_widget(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator["ProductListView", None, None]:
    from di.injector_module import get_injector
    from bridge.product import ProductBridge

    injector = get_injector()
    product_bridge: ProductBridge = injector.get(ProductBridge)

    widget = ProductListView(
        parent=None,
        product_bridge=product_bridge,
    )
    qtbot.addWidget(widget)
    widget.show()
    yield widget
    widget.deleteLater()
```

### Test File Structure (`tests/frontend/views/test_product_list.py`)

```python
from __future__ import annotations

import pytest
import pytestqt
from pytestqt.qtbot import QtBot

# Imports for inline widget construction (TC-01)
from bridge.product import ProductBridge
from di.injector_module import get_injector
from frontend.views.product_list import ProductListView

# Test classes follow:
# class TestProductListInitialLoad: ...
# class TestProductListSupplierFilter: ...
# class TestProductListProductNameFilter: ...
# class TestProductListMonthFilter: ...
# class TestProductListCombinedFilters: ...
# class TestProductListDisplayCorrectness: ...
# class TestProductListEmptyState: ...
# class TestProductListPagination: ...
# class TestProductListClearFilters: ...
# class TestProductListEnterKeySearch: ...
```

### Column Index Reference

| Column | Header | Type |
|--------|--------|------|
| 0 | Data | `dd/MM/yyyy` string |
| 1 | Fornecedor | Supplier name string |
| 2 | Produto | Product name string |
| 3 | Preço | Brazilian currency string (e.g., `"250,00"`) |
| 4 | Total | Brazilian currency string (e.g., `"250,00"`) |

### Assertion Patterns (from existing tests)

```python
# Row count
assert widget._model.rowCount() == expected_rows

# Cell text
assert widget._model.item(row, col).text() == expected_text

# Filter field text
assert widget.filter_supplier.text() == ""
assert widget.filter_product.text() == ""
assert widget.filter_month.text() == ""

# Pagination label
assert widget.page_label.text() == "Página 1 de 1"

# Button states
assert widget.btn_prev.isEnabled() is False
assert widget.btn_next.isEnabled() is True

# Internal state
assert widget._current_page == 1
assert widget._page_count == 1
```

### Type Hints

All functions and methods must have type hints, per project convention. The `pytestqt.qtbot.QtBot` type should be used (not the string `"QtBot"`).

---

## Dependencies Between Files

```
tests/conftest.py
  └── imports from tests/fixtures/products.py (product_list_widget)

tests/fixtures/products.py
  └── depends on tests/fixtures/database.py (temp_engine)
  └── imports bridge.product.ProductBridge
  └── imports frontend.views.product_list.ProductListView

tests/frontend/views/test_product_list.py
  └── depends on tests/fixtures/products.py (product_list_widget via conftest)
  └── imports bridge.product.ProductBridge (for TC-01 inline construction)
  └── imports di.injector_module.get_injector (for TC-01)
  └── imports frontend.views.product_list.ProductListView (for TC-01)
```

---

## Risks and Considerations

1. **Test DB isolation:** The `temp_engine` fixture seeds BOTH expenses and orders. Tests for ProductListView only query product data. This is fine — the seeded expenses don't interfere with product queries. However, if new expense-related tests are added later, they should not be affected.

2. **PAGE_SIZE = 50:** All 7 seeded products fit on a single page. Pagination navigation tests (TC-08) verify boundary behavior but don't test actual multi-page scrolling. If the plan were expanded, additional seed data would be needed.

3. **Normalized text matching:** The supplier filter uses `SUPPLIER_NORMALIZED` (accent-stripped, lowercase). Tests should use the normalized form of search terms (e.g., "cimento" not "Cimento") since the user types into the filter field and the bridge normalizes it. The tests use "Cimento" and "Areia" which normalize correctly.

4. **Date ordering:** Products are ordered by `Order.DATE DESC`. Within the same order date, products maintain insertion order (ID ascending). This means for Order A (2024-07-10), "Cimento CP-II 50kg" (prod-a1) comes before "Cimento CP-II 1kg" (prod-a2). Tests must account for this ordering.

5. **Currency format:** `cents_to_display()` produces strings like `"12,00"` (no "R$" prefix). Tests should assert the exact formatted string without "R$".

6. **Signal timing:** `returnPressed.emit()` is synchronous — the search completes before the next assertion. No `qtbot.wait()` needed.

7. **No `__init__.py` files:** `tests/fixtures/` and `tests/` are namespace packages. Direct imports work.

---

## Implementation Order

1. **Create `tests/fixtures/products.py`** — the `product_list_widget` fixture
2. **Update `tests/conftest.py`** — add import and export of `product_list_widget`
3. **Create `tests/frontend/views/test_product_list.py`** with TC-01 through TC-05 (initial load, filters)
4. **Add TC-06** (display correctness) — most comprehensive cell assertions
5. **Add TC-07 through TC-10** (empty state, pagination, clear, enter key)

This order ensures the fixture is available before tests are written, and the simplest tests come first, building up to the most comprehensive ones.

---

## Verification After Implementation

Run the test suite:
```powershell
.\.venv\Scripts\Activate.ps1 && pytest tests/frontend/views/test_product_list.py -v
```

All 10 test classes should pass. Additionally, run the full suite to ensure no regressions:
```powershell
.\.venv\Scripts\Activate.ps1 && pytest -v
```
