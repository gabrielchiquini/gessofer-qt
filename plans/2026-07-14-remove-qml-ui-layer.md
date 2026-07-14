# Implementation Plan: Remove QML UI Layer, Keep Procedural Qt UI

## Summary

This plan removes the entire QML UI layer (the `App/` directory and `src/backend/qml/` directory) from the Gessofer-Qt project, while preserving the procedural PySide6 Qt UI in `src/frontend/` and `src/widgets/`. The key challenge is that `qml_transformers.py` contains pure data-transformation functions used by both the QML layer (to be removed) and the widgets layer (to be kept). These transformer functions will be moved to `src/backend/utils/transformers.py` before the QML directory is deleted.

## Files to Delete

### 1. `App/` directory (10 files)
Delete the entire directory:
- `App/Main.qml`
- `App/MainTest.qml`
- `App/Constants.qml`
- `App/NavigationGroup.qml`
- `App/NavItem.qml`
- `App/ProductList.qml`
- `App/TopNavbar.qml`
- `App/WelcomeIcon.qml`
- `App/WelcomeScreen.qml`
- `App/qmldir`

### 2. `src/backend/qml/` directory (7 Python files + `__pycache__/`)
Delete the entire directory:
- `src/backend/qml/__init__.py`
- `src/backend/qml/qml_models.py`
- `src/backend/qml/qml_backend.py`
- `src/backend/qml/qml_fetch.py`
- `src/backend/qml/qml_save.py`
- `src/backend/qml/qml_business.py`
- `src/backend/qml/qml_transformers.py`

### 3. `gessofer.qmlproject` (55 lines)
Delete this QML project file — it is a Qt Creator/QDS project descriptor for the QML editor and has no relevance to the procedural UI.

### 4. `.qmllint.ini` (82 lines)
Delete this qmllint configuration file — it is only needed for linting QML files.

## Files to Create

### 1. `src/backend/utils/transformers.py`
**Purpose:** Replace `qml_transformers.py` with a location-independent module for pure data-transformation functions. These functions have no QML dependencies — they operate on ORM entities, DTOs, and service result types.

**Key contents:** Copy all 8 functions from `src/backend/qml/qml_transformers.py` verbatim (no logic changes):

| Function | Signature | Purpose |
|----------|-----------|---------|
| `orm_order_to_dict` | `(order: Order) -> dict[str, Any]` | Convert ORM Order to dict |
| `orm_product_to_dict` | `(product: Product) -> dict[str, Any]` | Convert ORM Product to dict |
| `product_list_item_to_dict` | `(product: Product) -> dict[str, Any]` | Convert Product for table display (includes order-level data + date formatting) |
| `dict_to_order_input` | `(d: dict[str, Any]) -> OrderInput` | Convert dict to OrderInput DTO |
| `expense_to_dict` | `(expense: Expense) -> dict[str, Any]` | Convert ORM Expense to dict |
| `product_page_to_dict` | `(response: PageResponse[Product]) -> dict[str, Any]` | Convert PageResponse[Product] to dict |
| `freight_result_to_dict` | `(result: FreightDistributionResult) -> dict[str, Any]` | Convert FreightDistributionResult to dict |
| `xml_import_result_to_dict` | `(result: XmlImportResult) -> dict[str, Any]` | Convert XmlImportResult to dict |

**Dependencies:** Imports from `backend.entities.orm`, `backend.models.dto`, `backend.services.freight_distribution`, `backend.services.xml_import_service`, `backend.utils.currency`, and `backend.utils.date` — all of which already exist and are unaffected.

**Add to `src/backend/utils/__init__.py`:** Re-export all 8 functions in the `__all__` list so existing import patterns (`from backend.utils import ...`) continue to work if any code uses that style. The `__init__.py` currently exports `cents_to_display`, `parse_currency_to_cents`, date functions, and `normalize_text`. Add the new transformer function names to the imports and `__all__`.

### 2. `src/backend/utils/__init__.py` (MODIFY)
**Current state:** Exports `cents_to_display`, `parse_currency_to_cents`, date functions, and `normalize_text`.

**Changes:**
- Add import line: `from .transformers import (dict_to_order_input, expense_to_dict, freight_result_to_dict, orm_order_to_dict, orm_product_to_dict, product_list_item_to_dict, product_page_to_dict, xml_import_result_to_dict)`
- Add these 8 names to the `__all__` list

## Files to Modify

### 1. `src/frontend/business.py`

**Current state:** 130 lines. Imports `QmlBusiness`, `QmlFetch`, `QmlSave` (which don't exist — these are broken imports), and transformer functions from `backend.qml.qml_transformers`. Contains:
- `_get_business_handler()` — unused function that tries to instantiate `QmlBusiness` (broken)
- `distribute_freight()` — uses `dict_to_order_input` and `freight_result_to_dict` from `backend.qml`
- `import_xml()` — uses `xml_import_result_to_dict` from `backend.qml`
- `validate_order()` — uses `dict_to_order_input` from `backend.qml`
- `validate_expense()` — no transformer dependency, uses `ValidationService` directly

**Changes needed:**
- **Remove all imports from `backend.qml`** (lines 6–13)
- **Remove the `_business_handler` global variable** (line 21) and `_get_business_handler()` function (lines 24–38) — this function is unused by any other file and references the non-existent `QmlBusiness` class
- **Update inline imports** within `distribute_freight()`, `import_xml()`, and `validate_order()` to import from `backend.utils.transformers` instead of `backend.qml.qml_transformers`
- **Simplify top-level imports:** Replace the block at lines 9–13 with a single import:
  ```python
  from backend.utils.transformers import (
      dict_to_order_input,
      freight_result_to_dict,
      xml_import_result_to_dict,
  )
  ```
- **Simplify inline imports:** Remove the local `from backend.qml.qml_transformers import ...` statements inside `distribute_freight()` (line 52), `import_xml()` (line 78), and `validate_order()` (line 99). Since the top-level imports now cover these, the local imports are redundant.

**Result:** The file shrinks from 130 lines to approximately 100 lines. The four business functions (`distribute_freight`, `import_xml`, `validate_order`, `validate_expense`) retain their exact behavior — only the import paths change.

### 2. `src/widgets/product.py`

**Current state:** 136 lines. Imports `product_page_to_dict, orm_order_to_dict` from `backend.qml.qml_transformers` (line 11).

**Changes needed:**
- **Line 11:** Replace `from backend.qml.qml_transformers import product_page_to_dict, orm_order_to_dict` with `from backend.utils.transformers import product_page_to_dict, orm_order_to_dict`

**Result:** Single-line change. No functional impact.

### 3. `src/widgets/order.py`

**Current state:** 70 lines. Imports `dict_to_order_input` from `backend.qml.qml_transformers` (line 8).

**Changes needed:**
- **Line 8:** Replace `from backend.qml.qml_transformers import dict_to_order_input` with `from backend.utils.transformers import dict_to_order_input`

**Result:** Single-line change. No functional impact.

### 4. `src/widgets/expense.py`

**Current state:** 134 lines. Imports `expense_to_dict` from `backend.qml.qml_transformers` (line 11).

**Changes needed:**
- **Line 11:** Replace `from backend.qml.qml_transformers import expense_to_dict` with `from backend.utils.transformers import expense_to_dict`

**Result:** Single-line change. No functional impact.

### 5. `tests/conftest.py`

**Current state:** 182 lines. Imports `FetchHandler` from `backend.qml.qml_fetch` (line 11). The tests use `FetchHandler` to seed test data into the database.

**Changes needed:**
- **Line 11:** Replace `from backend.qml.qml_fetch import FetchHandler` with `from widgets.product import FetchHandler`

**Rationale:** The `FetchHandler` class in `src/widgets/product.py` has the same interface as the one in `backend.qml.qml_fetch` (both accept a `session_factory` callable and provide `fetch_products()` and `fetch_orders_for_month()` methods). The tests use `FetchHandler` to seed data and call `fetch_products()` — both of which work identically in the widgets version. The `conftest.py` fixtures (`seeded_fetch_handler`, `fetch_handler`, `sample_page`) will continue to function.

### 6. `tests/test_product_list.py`

**Current state:** 169 lines. Imports `FetchHandler` from `backend.qml.qml_fetch` (line 5) and `product_page_to_dict` from `backend.qml.qml_transformers` (line 6).

**Changes needed:**
- **Line 5:** Replace `from backend.qml.qml_fetch import FetchHandler` with `from widgets.product import FetchHandler`
- **Line 6:** Replace `from backend.qml.qml_transformers import product_page_to_dict` with `from backend.utils.transformers import product_page_to_dict`

**Result:** Two import-line changes. No test logic changes.

### 7. `pyproject.toml`

**Current state:** 5 lines. Contains `[tool.pyside6-project]` section referencing QML files.

**Changes needed:**
- **Line 5:** Replace `files = ["src/main.py", "App/Main.qml", "App/qmldir"]` with `files = ["src/main.py"]`

**Result:** Single-line change. Removes stale QML file references from the PySide6 project config.

## Files to Keep (No Changes)

| File | Reason |
|------|--------|
| `src/main.py` | Already uses procedural UI, no QML references |
| `src/frontend/app.py` | Procedural Qt UI (QMainWindow) |
| `src/frontend/constants.py` | Navigation data and constants |
| `src/frontend/product_list.py` | Procedural Qt UI (QWidget + QTableView) |
| `src/frontend/navbar.py` | Procedural Qt UI (QMenuBar) |
| `src/frontend/__init__.py` | Re-exports MainWindow |
| `src/widgets/__init__.py` | Re-exports widget functions |
| `src/widgets/product.py` | Modified (import path only) |
| `src/widgets/order.py` | Modified (import path only) |
| `src/widgets/expense.py` | Modified (import path only) |
| `src/backend/entities/orm.py` | ORM models — untouched |
| `src/backend/injector_module.py` | DI container — untouched |
| `src/backend/models/dto.py` | DTOs — untouched |
| `src/backend/repositories/` | Repository classes — untouched |
| `src/backend/services/` | Service classes — untouched |
| `src/backend/utils/currency.py` | Currency utilities — untouched |
| `src/backend/utils/date.py` | Date utilities — untouched |
| `src/backend/utils/text.py` | Text utilities — untouched |
| `src/backend/database/` | Database connection — untouched |
| `src/backend/errors.py` | Error types — untouched |
| `conftest.py` | Root conftest (adds `src/` to path) — untouched |

## Import Update Summary

Every file that previously imported from `backend.qml` will be updated as follows:

| File | Old Import | New Import |
|------|-----------|------------|
| `src/frontend/business.py` | `from backend.qml.qml_business import QmlBusiness` | **REMOVED** (unused, broken) |
| `src/frontend/business.py` | `from backend.qml.qml_fetch import QmlFetch` | **REMOVED** (unused, broken) |
| `src/frontend/business.py` | `from backend.qml.qml_save import QmlSave` | **REMOVED** (unused, broken) |
| `src/frontend/business.py` | `from backend.qml.qml_transformers import ...` | `from backend.utils.transformers import ...` |
| `src/widgets/product.py` | `from backend.qml.qml_transformers import ...` | `from backend.utils.transformers import ...` |
| `src/widgets/order.py` | `from backend.qml.qml_transformers import ...` | `from backend.utils.transformers import ...` |
| `src/widgets/expense.py` | `from backend.qml.qml_transformers import ...` | `from backend.utils.transformers import ...` |
| `tests/conftest.py` | `from backend.qml.qml_fetch import FetchHandler` | `from widgets.product import FetchHandler` |
| `tests/test_product_list.py` | `from backend.qml.qml_fetch import FetchHandler` | `from widgets.product import FetchHandler` |
| `tests/test_product_list.py` | `from backend.qml.qml_transformers import product_page_to_dict` | `from backend.utils.transformers import product_page_to_dict` |

## Implementation Order

Execute in this sequence to maintain a working state at each step:

### Step 1: Create `src/backend/utils/transformers.py`
Copy all 8 functions from `src/backend/qml/qml_transformers.py` into the new file. No modifications to the function bodies.

### Step 2: Update `src/backend/utils/__init__.py`
Add the transformer function imports and exports.

### Step 3: Update `src/frontend/business.py`
Remove all `backend.qml` imports, remove `_get_business_handler()`, update the remaining imports to use `backend.utils.transformers`.

### Step 4: Update `src/widgets/product.py`
Change the single import line.

### Step 5: Update `src/widgets/order.py`
Change the single import line.

### Step 6: Update `src/widgets/expense.py`
Change the single import line.

### Step 7: Update `tests/conftest.py`
Change the `FetchHandler` import to use `widgets.product`.

### Step 8: Update `tests/test_product_list.py`
Change both import lines.

### Step 9: Update `pyproject.toml`
Remove QML file references.

### Step 10: Delete `App/` directory
Delete all 10 QML files and `qmldir`.

### Step 11: Delete `src/backend/qml/` directory
Delete all 7 Python files and `__pycache__/`.

### Step 12: Delete `gessofer.qmlproject`
Delete the QML project file.

### Step 13: Delete `.qmllint.ini`
Delete the qmllint configuration file.

### Step 14: Clean up `__pycache__/` directories
Remove stale `.pyc` files under `src/backend/qml/__pycache__/` (already handled by directory deletion) and any other stale caches.

## Verification Steps

### 1. Import verification (quick check)
```powershell
.\.venv\Scripts\Activate.ps1
python -c "from frontend.app import MainWindow; print('OK: MainWindow imported')"
python -c "from widgets.product import fetch_products; print('OK: fetch_products imported')"
python -c "from widgets.order import save_orders; print('OK: save_orders imported')"
python -c "from widgets.expense import save_expenses, fetch_expenses_for_month; print('OK: expense imports')"
python -c "from frontend.business import distribute_freight, import_xml, validate_order, validate_expense; print('OK: business imports')"
python -c "from backend.utils.transformers import dict_to_order_input, expense_to_dict, product_page_to_dict, orm_order_to_dict, freight_result_to_dict, xml_import_result_to_dict; print('OK: transformer imports')"
```

### 2. App launch verification
```powershell
.\.venv\Scripts\Activate.ps1
python src/main.py
```
The application should launch without errors and display the main window with the navigation bar and product list.

### 3. Test suite verification
```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
```
All existing tests should pass. The `conftest.py` and `test_product_list.py` fixtures use `FetchHandler` from `widgets.product` and `product_page_to_dict` from `backend.utils.transformers` — both of which have the same interfaces as their `backend.qml` predecessors.

### 4. No remaining QML references
```powershell
grep -r "backend\.qml" src/ tests/ --include="*.py"
```
This should return zero results. Any match indicates a missed import.

### 5. No remaining QML file references
```powershell
grep -r "App/" src/ --include="*.py"
grep -r "qmldir" src/ --include="*.py"
grep -r "loadFromModule" src/ --include="*.py"
```
These should all return zero results.

## Risks and Considerations

### Risk 1: `FetchHandler` in `widgets.product` vs `qml_fetch.py`
The `FetchHandler` class in `src/widgets/product.py` has the same constructor signature (`__init__(self, session_factory: Callable[[], Session])`) and the same public methods (`fetch_products`, `fetch_orders_for_month`) as the one in `backend.qml.qml_fetch`. The tests use `FetchHandler` to seed data and call `fetch_products()` — both operations work identically. The `fetch_orders_for_month` method in `widgets.product` returns `list[dict[str, Any]]` (transformed via `orm_order_to_dict`) while `qml_fetch` returns raw `list[Order]` ORM entities. However, the test fixtures (`conftest.py`) only call `fetch_products()` and access `handler._session_factory` for seeding — neither of these is affected by the return type difference.

### Risk 2: Stale `__pycache__/` directories
After deleting `src/backend/qml/`, old `.pyc` files may linger if the directory isn't fully removed. The deletion step should remove the entire directory including `__pycache__/`.

### Risk 3: `pyproject.toml` PySide6 project tool
The `[tool.pyside6-project]` section is used by the PySide6 tooling for project configuration. Removing the QML file references is correct since the app no longer uses QML. If the PySide6 project tool is not actually used in this project's workflow, this change is harmless.

### Risk 4: No scope creep
This plan only removes QML-related code and updates imports. It does NOT:
- Refactor any business logic
- Change the database schema
- Modify the ORM models
- Change the service layer
- Add new features
- Modify any files outside those explicitly listed above

## Known Limitations

- **No QML tooling support:** After this change, `qmllint`, Qt Creator QML editing, and the `.qmlproject` file are no longer relevant. The `.qmllint.ini` and `gessofer.qmlproject` files are deleted.
- **Plans directory:** The `plans/` directory contains historical implementation plans that reference `backend.qml`. These are documentation artifacts and are not executed or imported by the application. They are left in place as historical records.
- **Docs directory:** The `docs/` directory contains Tauri-era documentation that references QML. These are also documentation artifacts and are left in place.
