# Implementation Plan: Replace `dict[str, Any]` Return Types with TypedDicts in the Bridge Layer

## Summary

This plan introduces `TypedDict` definitions for every dictionary shape produced by the `src/backend/qml/` bridge layer and propagates them through all consumers. A new file `src/backend/qml/qml_types.py` will hold all TypedDict definitions, and every transformer function, `BackendManager` slot, widget-layer function, and frontend-layer function will be updated to use them. The `frontend/` layer (which still exists as a PySide6 widget-based UI) is also updated because it consumes the same dict shapes.

## Files to Create

### `src/backend/qml/qml_types.py`

**Purpose:** Central module that defines all `TypedDict` types used by the bridge layer. Each TypedDict documents the exact key set and value type for one dict shape.

**Key contents:**

```python
from __future__ import annotations

from typing import List, NotRequired, TypedDict


class ProductDict(TypedDict):
    """Shape produced by orm_product_to_dict()."""
    id: str
    name: str
    quantity: int
    price: int          # cents
    total: int          # cents
    order_id: str
    itemOrdinal: int | None


class OrderDict(TypedDict):
    """Shape produced by orm_order_to_dict()."""
    id: str
    date: str           # ISO 8601 (YYYY-MM-DD)
    supplier: str
    nfeKey: str
    freight: int        # cents
    unloading: int      # cents
    products: List[ProductDict]


class ProductListItemDict(TypedDict):
    """Shape produced by product_list_item_to_dict(). Distinct from ProductDict —
    contains order-level data and display-formatted currency strings."""
    date: str           # dd/MM/yyyy (Brazilian format)
    supplier: str
    name: str
    price: str          # display-formatted (e.g. "R$ 1.234,56")
    totalPrice: str     # display-formatted
    orderId: str


class ExpenseDict(TypedDict):
    """Shape produced by expense_to_dict()."""
    id: int
    month: str
    description: str
    value: int          # cents


class ProductPageDict(TypedDict):
    """Shape produced by product_page_to_dict()."""
    items: List[ProductListItemDict]
    page: int
    page_count: int
    total: int
    page_size: int


class FreightResultDict(TypedDict):
    """Shape produced by freight_result_to_dict()."""
    order_id: str
    old_freight: int
    old_unloading: int
    ratio: float
    products_total_before: int
    products_total_after: int
    new_products: List[ProductDict]


class XmlImportResultDict(TypedDict):
    """Shape produced by xml_import_result_to_dict()."""
    orders: List[OrderDict]
    warnings: List[str]


class ValidationResultDict(TypedDict):
    """Shape returned by validate_order() and validate_expense()."""
    valid: bool
    errors: List[str]
```

**Design notes:**
- `ProductDict` and `ProductListItemDict` are **separate** TypedDicts because they have different fields and value types (raw ints vs. display-formatted strings).
- `itemOrdinal` in `ProductDict` is `int | None` because the ORM column is nullable.
- `nfeKey` in `OrderDict` is `str` (never `None`) because `orm_order_to_dict` returns `""` for null keys.
- `orderId` in `ProductListItemDict` uses the camelCase key `orderId` (matching the existing dict key, not the ORM column name `ORDER_ID`).
- `totalPrice` in `ProductListItemDict` uses camelCase (matching existing code).
- `price` and `totalPrice` in `ProductListItemDict` are `str` because `cents_to_display()` converts them.
- No `NotRequired` fields are needed — all fields are always present in the produced dicts.

**Dependencies:** No imports from other project modules. Pure typing definitions.

---

## Files to Modify

### 1. `src/backend/qml/qml_transformers.py`

**Current state:** Contains 7 functions that return `dict[str, Any]`. Also imports `Any` from `typing`.

**Changes:**

1. **Add import for TypedDicts:**
   ```python
   from backend.qml.qml_types import (
       ExpenseDict,
       FreightResultDict,
       OrderDict,
       ProductDict,
       ProductListItemDict,
       ProductPageDict,
       ValidationResultDict,
       XmlImportResultDict,
   )
   ```

2. **Remove `from typing import Any`** — no longer needed.

3. **Update function signatures and return statements:**

   | Function | Old Return | New Return | Change Details |
   |---|---|---|---|
   | `orm_order_to_dict` | `dict[str, Any]` | `OrderDict` | Return type annotation only; body unchanged (still builds a plain `dict` at runtime, but type-checker now knows the shape) |
   | `orm_product_to_dict` | `dict[str, Any]` | `ProductDict` | Same |
   | `product_list_item_to_dict` | `dict[str, Any]` | `ProductListItemDict` | Same |
   | `expense_to_dict` | `dict[str, Any]` | `ExpenseDict` | Same |
   | `product_page_to_dict` | `dict[str, Any]` | `ProductPageDict` | Same |
   | `freight_result_to_dict` | `dict[str, Any]` | `FreightResultDict` | Same |
   | `xml_import_result_to_dict` | `dict[str, Any]` | `XmlImportResultDict` | Same |

4. **Update `dict_to_order_input`:**
   - Parameter type: `d: dict[str, Any]` → `d: OrderDict`
   - This is safe because callers always pass the output of `orm_order_to_dict()` or `xml_import_result_to_dict()`, both of which produce `OrderDict`-shaped dicts.
   - Body: No changes needed; all `.get()` calls still work on `OrderDict`.

**Rationale:** The transformers are the production point of all bridge-layer dicts. Changing their return types to TypedDicts gives the type checker full knowledge of the shapes, which cascades to every consumer.

---

### 2. `src/backend/qml/qml_backend.py`

**Current state:** `BackendManager` class with Slot methods returning `dict[str, Any]`. Imports `Any` from `typing`.

**Changes:**

1. **Add TypedDict imports:**
   ```python
   from backend.qml.qml_types import (
       ExpenseDict,
       FreightResultDict,
       OrderDict,
       ProductPageDict,
       ValidationResultDict,
       XmlImportResultDict,
   )
   ```

2. **Remove `from typing import Any`** (if it's the only use of `Any` in this file).

3. **Update method signatures:**

   | Method | Old Return | New Return |
   |---|---|---|
   | `orders_for_month` | `list[dict[str, Any]]` | `list[OrderDict]` |
   | `product_list` | `dict[str, Any]` | `ProductPageDict` |
   | `expenses_for_month` | `list[dict[str, Any]]` | `list[ExpenseDict]` |
   | `distribute_freight` | `dict[str, Any]` | `FreightResultDict` |
   | `import_xml` | `dict[str, Any]` | `XmlImportResultDict` |
   | `validate_order` | `dict[str, Any]` | `ValidationResultDict` |
   | `validate_expense` | `dict[str, Any]` | `ValidationResultDict` |

4. **Update the `@Slot` decorators to reflect the new types** — the `@Slot` decorator accepts type names or Python types. The existing `@Slot(str)`, `@Slot(int, str, str, str)`, etc. signatures are fine since they deal with input parameters. The return types are only annotations.

5. **Error-path return values** must match the TypedDict shape:
   - `distribute_freight`: `return {}` → should be `return FreightResultDict(order_id="", old_freight=0, old_unloading=0, ratio=0.0, products_total_before=0, products_total_after=0, new_products=[])` — but since this is an error path and the dict is empty, the type checker will flag it. **Decision:** Keep `return {}` for now — it's a runtime error path that shouldn't be reached. The type checker with `--ignore-missing-imports` or a `# type: ignore[return-value]` comment can suppress this. Alternatively, construct a minimal valid dict. We recommend constructing a minimal valid dict for correctness.
   - `import_xml`: `return {"orders": [], "warnings": []}` — already matches `XmlImportResultDict` shape.
   - `validate_order` (error path): `return {"valid": False, "errors": [str(exc)]}` — already matches `ValidationResultDict` shape.

**Rationale:** `BackendManager` is the composition root for the PySide6 layer. Its Slot methods are the public API surface that widgets and frontend code call. TypedDict return types here ensure callers get full type safety.

---

### 3. `src/backend/qml/qml_models.py`

**Current state:** Contains `OrderListModel`, `ExpenseListModel`, and `ProductListModel` — Qt model classes that store data as `list[dict[str, Any]]`. These are QML-accessible models that are still registered via `qmlRegisterType`.

**Changes:**

1. **Add TypedDict imports:**
   ```python
   from backend.qml.qml_types import (
       ExpenseDict,
       OrderDict,
       ProductListItemDict,
   )
   ```

2. **Update internal storage types:**

   | Class | Old Type | New Type |
   |---|---|---|
   | `OrderListModel` | `self._orders: list[dict[str, Any]] = []` | `self._orders: list[OrderDict] = []` |
   | `ExpenseListModel` | `self._expenses: list[dict[str, Any]] = []` | `self._expenses: list[ExpenseDict] = []` |
   | `ProductListModel` | `self._items: list[dict[str, Any]] = []` | `self._items: list[ProductListItemDict] = []` |

3. **Update `OrderListModel.load_for_month()`:** The dict-building code inside `load_for_month` currently builds dicts with display-formatted currency strings (`cents_to_display()`). However, `OrderDict` expects raw int values for `freight` and `unloading`, and raw `ProductDict` entries (which also have raw ints). **Important:** The current `load_for_month` builds dicts with `cents_to_display()` for freight/unloading and products — this means the shape doesn't match `OrderDict`.

   **Decision:** Keep the internal storage as-is (the model needs display-formatted values for QML). But since the TypedDicts are for the **bridge layer's contract**, the model's internal data doesn't need to match `OrderDict`. Instead, we should use a **separate type alias** or simply leave the model's internal storage as `list[dict[str, Any]]` with a comment, OR define a display-oriented TypedDict.

   **Recommended approach:** Since the Qt models are internal implementation details and not part of the bridge-layer contract, leave their internal storage as `list[dict[str, Any]]` but add a type comment or `# noqa` if needed. The key change is updating the `ProductListModel.refresh()` method's result handling:

   - `refresh()`: `result.get("items", [])` — the `result` is now typed as `ProductPageDict`, so `result["items"]` returns `list[ProductListItemDict]`. Update:
     ```python
     self._items = result["items"]  # No .get() needed; TypedDict guarantees the key
     ```

4. **Update `ExpenseListModel.load_for_month()`:** Similarly, the current code builds dicts with `cents_to_display(expense.VALUE)` — but `ExpenseDict` expects `value: int`. The model's internal data doesn't match the TypedDict. **Decision:** Same as above — leave internal storage as `list[dict[str, Any]]` with a comment noting that the model transforms data for QML display.

**Rationale for keeping model internals as `dict[str, Any]`:** The Qt model classes transform ORM entities into display-ready dicts (with formatted currency strings, Brazilian date strings, etc.). These shapes are **different** from the TypedDicts in `qml_types.py` which represent the bridge-layer API contract. The models are internal implementation details, not part of the public contract. Changing them to use TypedDicts would require either:
- Defining separate "display" TypedDicts (overkill for internal use)
- Storing display-formatted values in TypedDict fields typed as `int` (incorrect)

The safest approach is to leave the model internals as `dict[str, Any]` but update the `refresh()` method to use the TypedDict `ProductPageDict` for the result it receives from `BackendManager.product_list()`.

---

### 4. `src/backend/qml/__init__.py`

**Current state:**
```python
from backend.qml.qml_models import ExpenseListModel, OrderListModel

__all__ = ["OrderListModel", "ExpenseListModel"]
```

**Changes:**

1. **Add TypedDict exports:**
   ```python
   from backend.qml.qml_types import (
       ExpenseDict,
       FreightResultDict,
       OrderDict,
       ProductDict,
       ProductListItemDict,
       ProductPageDict,
       ValidationResultDict,
       XmlImportResultDict,
   )

   __all__ = [
       "ExpenseDict",
       "ExpenseListModel",
       "FreightResultDict",
       "OrderDict",
       "OrderListModel",
       "ProductDict",
       "ProductListItemDict",
       "ProductPageDict",
       "ValidationResultDict",
       "XmlImportResultDict",
   ]
   ```

**Rationale:** Consumers can now import TypedDicts from a single well-known location.

---

### 5. `src/widgets/order.py`

**Current state:** Imports `dict_to_order_input` from `qml_transformers`. The `save_orders` function takes `orders: list[dict[str, Any]]`.

**Changes:**

1. **Add TypedDict import:**
   ```python
   from backend.qml.qml_types import OrderDict
   ```

2. **Update `save_orders` signature:**
   ```python
   def save_orders(
       orders: list[OrderDict],
       deleted_order_ids: list[str],
   ) -> bool:
   ```

3. **Update `dict_to_order_input` call:** The function now accepts `OrderDict` instead of `dict[str, Any]`, which is correct because callers pass `OrderDict`-shaped dicts.

**Rationale:** The widget layer's `save_orders` function receives order data from the UI. After this change, the type checker will enforce that only `OrderDict`-shaped dicts are passed.

---

### 6. `src/widgets/expense.py`

**Current state:** Imports `expense_to_dict` from `qml_transformers`. `_ExpenseFetchHandler.fetch_expenses_for_month` returns `list[dict[str, Any]]`. `fetch_expenses_for_month` returns `list[dict[str, Any]]`. `save_expenses` takes `expenses: list[dict[str, Any]]`.

**Changes:**

1. **Add TypedDict imports:**
   ```python
   from backend.qml.qml_types import ExpenseDict
   ```

2. **Update `_ExpenseFetchHandler.fetch_expenses_for_month`:**
   ```python
   def fetch_expenses_for_month(self, month: str) -> list[ExpenseDict]:
   ```

3. **Update `fetch_expenses_for_month`:**
   ```python
   def fetch_expenses_for_month(month: str) -> list[ExpenseDict]:
   ```

4. **Update `save_expenses`:**
   ```python
   def save_expenses(
       expenses: list[ExpenseDict],
       month: str,
   ) -> bool:
   ```

5. **Update dict access in `save_expenses`:** The line `ExpenseInput(description=e["description"], value=e["value"])` — since `ExpenseDict` has `description: str` and `value: int`, the bracket access is now type-safe.

**Rationale:** Same as order.py — enforce the shape at the type level.

---

### 7. `src/widgets/product.py`

**Current state:** Imports `product_page_to_dict` and `orm_order_to_dict` from `qml_transformers`. `FetchHandler.fetch_products` returns `dict[str, Any]`. `FetchHandler.fetch_orders_for_month` returns `list[dict[str, Any]]`. Module-level `fetch_products` returns `dict[str, Any]`. `fetch_orders_for_month` returns `list[dict[str, Any]]`.

**Changes:**

1. **Add TypedDict imports:**
   ```python
   from backend.qml.qml_types import OrderDict, ProductPageDict
   ```

2. **Update `FetchHandler.fetch_products`:**
   ```python
   def fetch_products(
       self,
       page: int,
       supplier: str | None = None,
       product: str | None = None,
       month: str | None = None,
   ) -> ProductPageDict:
   ```

3. **Update `FetchHandler.fetch_orders_for_month`:**
   ```python
   def fetch_orders_for_month(self, month: str) -> list[OrderDict]:
   ```

4. **Update module-level `fetch_products`:**
   ```python
   def fetch_products(
       page: int,
       supplier: str = "",
       product: str = "",
       month: str = "",
   ) -> ProductPageDict:
   ```

5. **Update the error-path return in `fetch_products`:**
   ```python
   return ProductPageDict(
       items=[],
       page=page,
       page_count=0,
       total=0,
       page_size=50,
   )
   ```

6. **Update module-level `fetch_orders_for_month`:**
   ```python
   def fetch_orders_for_month(month: str) -> list[OrderDict]:
   ```

**Rationale:** The widget layer's product functions are the bridge between the UI and the backend. TypedDict return types ensure the UI layer (which receives these through `frontend/product_list.py`) gets type-checked data.

---

### 8. `src/frontend/business.py`

**Current state:** Contains `distribute_freight`, `import_xml`, `validate_order`, `validate_expense` functions that return `dict[str, Any]`. Also imports transformers from `qml_transformers`.

**Changes:**

1. **Add TypedDict imports:**
   ```python
   from backend.qml.qml_types import (
       FreightResultDict,
       ValidationResultDict,
       XmlImportResultDict,
   )
   ```

2. **Update function signatures:**

   | Function | Old Return | New Return |
   |---|---|---|
   | `distribute_freight` | `dict[str, Any]` | `FreightResultDict` |
   | `import_xml` | `dict[str, Any]` | `XmlImportResultDict` |
   | `validate_order` | `dict[str, Any]` | `ValidationResultDict` |
   | `validate_expense` | `dict[str, Any]` | `ValidationResultDict` |

3. **Update error-path returns:**
   - `distribute_freight`: `return {}` → construct a minimal `FreightResultDict`
   - `import_xml`: `return {"orders": [], "warnings": []}` → already matches shape
   - `validate_order`: `return {"valid": False, "errors": [str(exc)]}` → already matches shape
   - `validate_expense`: `return {"valid": False, "errors": [str(exc)]}` → already matches shape

4. **Update `distribute_freight` input type:** The `order: dict[str, Any]` parameter → `order: OrderDict` (add `OrderDict` to imports).

5. **Remove `from typing import Any`** if it's no longer needed.

**Rationale:** This frontend business layer is a separate code path from `BackendManager` that directly calls services. It should use the same TypedDicts for consistency.

---

### 9. `src/frontend/product_list.py`

**Current state:** `_process_result` takes `result: dict[str, Any]` and accesses keys like `result["total"]`, `result["page_count"]`, `result.get("items", [])`, etc.

**Changes:**

1. **Add TypedDict import:**
   ```python
   from backend.qml.qml_types import ProductPageDict
   ```

2. **Update `_process_result` signature:**
   ```python
   def _process_result(self, result: ProductPageDict) -> None:
   ```

3. **Update dict access:** Since `ProductPageDict` is a TypedDict, all keys are guaranteed to exist. Replace:
   ```python
   self._total = result["total"]
   self._page_count = result["page_count"]
   for item in result.get("items", []):
   ```
   With:
   ```python
   self._total = result["total"]
   self._page_count = result["page_count"]
   for item in result["items"]:
   ```

4. **Update `item` access in the loop:** Since `item` is now typed as `ProductListItemDict`, the bracket accesses like `item.get("date", "")` can become `item["date"]`. The `cents_to_display(item.get("price", 0))` call needs attention: `ProductListItemDict` has `price: str` (already display-formatted), so `cents_to_display()` should **not** be called on it.

   **Critical fix needed:** The current code does:
   ```python
   QStandardItem(cents_to_display(item.get("price", 0))),
   QStandardItem(cents_to_display(item.get("totalPrice", 0))),
   ```
   But `ProductListItemDict` has `price: str` and `totalPrice: str` — these are **already** display-formatted by `cents_to_display()` in `product_list_item_to_dict()`. Calling `cents_to_display()` again on a string will cause a runtime error.

   **Fix:** Change to:
   ```python
   QStandardItem(item["price"]),
   QStandardItem(item["totalPrice"]),
   ```

5. **Update `orderId` access:** `item.get("orderId", "")` → `item["orderId"]` (TypedDict guarantees the key).

**Rationale:** This is a **bug fix** as well as a type safety improvement. The TypedDict makes it clear that `price` and `totalPrice` are already formatted strings, preventing the double-formatting bug.

---

### 10. `src/frontend/app.py`

**Current state:** No direct dict access. Only imports from `frontend.navbar` and `frontend.product_list`.

**Changes:** None required.

---

### 11. `tests/test_product_list.py`

**Current state:** Uses `product_page_to_dict` and checks dict keys via `d["items"]`, `d["page"]`, etc.

**Changes:**

1. **Add TypedDict import:**
   ```python
   from backend.qml.qml_types import ProductPageDict
   ```

2. **Type annotations for test variables** (optional but recommended):
   ```python
   def test_transformer_produces_correct_keys(self, sample_page: PageResponse) -> None:
       d: ProductPageDict = product_page_to_dict(sample_page)
   ```

3. **Update key assertions:** Since TypedDicts have guaranteed keys, `d["items"]` is preferred over `assert "items" in d`. However, the `in` checks are still valid and help document expected behavior. Leave them as-is for test clarity.

**Rationale:** Tests benefit from TypedDicts because the type checker will catch if the transformer returns a dict missing required keys.

---

## Files to Delete

**None.** No files need to be deleted. The `src/backend/qml/` directory and its contents remain — only the type annotations change.

---

## Data Model Changes

No database schema changes. No new models. Only type-level changes via `TypedDict` definitions.

---

## API Changes

The public API surface of the bridge layer changes from opaque `dict[str, Any]` returns to explicit TypedDict returns. This is a **non-breaking change** for runtime behavior — the actual dicts produced are identical. The change is purely at the type-checking level.

**New exports from `backend.qml`:**
- `ExpenseDict`, `FreightResultDict`, `OrderDict`, `ProductDict`, `ProductListItemDict`, `ProductPageDict`, `ValidationResultDict`, `XmlImportResultDict`

**Modified function signatures (type-only changes):**
- All transformer functions: `-> dict[str, Any]` → `-> <TypedDict>`
- All `BackendManager` Slot methods: same pattern
- All widget-layer fetch/save functions: same pattern
- All frontend business functions: same pattern

---

## State Management Changes

No new state management. The `qml_models.py` Qt model classes retain their internal `list[dict[str, Any]]` storage (as explained above, because their data shape differs from the TypedDicts — they store display-formatted values).

---

## Testing Considerations

### Existing tests that need no changes:
- `tests/test_product_list.py` — The `TestProductListTransformer` tests check dict keys at runtime. They will continue to work because the runtime dict shape is unchanged. Adding TypedDict annotations to test variables is optional.

### New tests to consider:
1. **TypedDict shape tests** — For each TypedDict, write a test that verifies the transformer produces a dict with exactly the expected keys and correct value types. This is a safety net in case a transformer is accidentally modified.
2. **Round-trip test** — Verify that `orm_order_to_dict` → `dict_to_order_input` → `orm_order_to_dict` produces a consistent result.

### Verification steps:
1. **Type check:** Run `mypy src/backend/qml/ src/widgets/ src/frontend/` (or `pyright` if preferred). All files should pass with zero errors.
2. **Run existing tests:** `pytest tests/` — all existing tests should pass (no behavioral changes).
3. **Run the app:** `python src/main.py` (or the frontend entry point) — verify the UI loads and functions correctly.
4. **Test the product list double-formatting fix:** Navigate to a product list page and verify prices display correctly (not double-formatted like "R$ R$ 1.234,56").

---

## Risks and Considerations

### 1. **Qt model internal types vs. TypedDict shapes**
The `OrderListModel` and `ExpenseListModel` build dicts with display-formatted currency strings (`cents_to_display()`), which differ from `OrderDict` and `ExpenseDict` (which have raw ints). **Mitigation:** Leave model internals as `list[dict[str, Any]]` with a clarifying comment. The TypedDicts represent the bridge-layer contract, not the model's internal representation.

### 2. **`distribute_freight` error path returning `{}`**
An empty dict doesn't match `FreightResultDict`. **Mitigation:** Construct a minimal valid `FreightResultDict` in the error path. This is a rare code path (only triggered by `ValueError` from the freight service) and shouldn't affect normal operation.

### 3. **`frontend/product_list.py` double-formatting bug**
The current code calls `cents_to_display()` on values that are already formatted strings. **This is a pre-existing bug** that the TypedDict change will expose. The fix (using `item["price"]` directly instead of `cents_to_display(item["price"])`) is included in this plan.

### 4. **`dict_to_order_input` parameter type**
Changing from `dict[str, Any]` to `OrderDict` is safe because all callers pass the output of `orm_order_to_dict()` or data that was built with the same shape. If a future caller passes a dict missing a required key, the type checker will catch it at the call site.

### 5. **`NotRequired` fields**
No fields are currently optional in any of the produced dicts. All fields are always present (null ORM values are converted to defaults: `""` for strings, `0` for ints, `[]` for lists). If optional fields are added in the future, they should use `NotRequired`.

### 6. **`@Slot` decorator compatibility**
PySide6's `@Slot` decorator works with the function's runtime behavior, not its type annotations. Changing return types from `dict[str, Any]` to TypedDicts does not affect `@Slot` behavior because Python dicts are still dicts at runtime.

---

## Implementation Order

Suggested sequence to minimize risk and maintain a working state at each step:

1. **Create `src/backend/qml/qml_types.py`** — The foundation. No other changes depend on it being complete.

2. **Update `src/backend/qml/qml_transformers.py`** — Update all transformer functions to use TypedDict returns. Run mypy to verify.

3. **Update `src/backend/qml/__init__.py`** — Export the new types.

4. **Update `src/backend/qml/qml_backend.py`** — Update `BackendManager` method return types.

5. **Update `src/backend/qml/qml_models.py`** — Update `ProductListModel.refresh()` to use `ProductPageDict`. Leave internal storage as-is.

6. **Update `src/widgets/order.py`** — Update `save_orders` parameter type.

7. **Update `src/widgets/expense.py`** — Update fetch and save function types.

8. **Update `src/widgets/product.py`** — Update fetch function types and error-path return.

9. **Update `src/frontend/business.py`** — Update function types.

10. **Update `src/frontend/product_list.py`** — Update `_process_result` type AND fix the double-formatting bug.

11. **Update `tests/test_product_list.py`** — Optional: add TypedDict annotations to test variables.

12. **Verify:** Run mypy, pytest, and the app.

---

## Verification Checklist

- [ ] `mypy src/backend/qml/qml_types.py` — passes
- [ ] `mypy src/backend/qml/qml_transformers.py` — passes
- [ ] `mypy src/backend/qml/qml_backend.py` — passes
- [ ] `mypy src/backend/qml/qml_models.py` — passes
- [ ] `mypy src/backend/qml/__init__.py` — passes
- [ ] `mypy src/widgets/order.py` — passes
- [ ] `mypy src/widgets/expense.py` — passes
- [ ] `mypy src/widgets/product.py` — passes
- [ ] `mypy src/frontend/business.py` — passes
- [ ] `mypy src/frontend/product_list.py` — passes
- [ ] `pytest tests/` — all existing tests pass
- [ ] App launches without errors
- [ ] Product list displays prices correctly (no double-formatting)
- [ ] Order save, expense save, freight distribution, XML import, and validation all function as before
