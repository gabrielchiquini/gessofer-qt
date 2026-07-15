# Implementation Plan: Remove `src/backend/utils/transformers.py`

## Summary

This plan removes the centralized `src/backend/utils/transformers.py` file by distributing its 8 transformation functions into their respective domain modules (`src/widgets/order.py`, `src/widgets/product.py`, `src/widgets/expense.py`, and `src/frontend/business.py`). Each function is tightly coupled to its domain and logically belongs alongside the widget that consumes its output. The bridge/dict TypedDict definitions in `src/bridge/__init__.py` remain untouched — they are shared contracts, not transformation logic.

## Function Placement Map

| Function | Target File | Reason |
|---|---|---|
| `orm_order_to_dict` | `src/widgets/product.py` | Used by `FetchHandler.fetch_orders_for_month()` |
| `orm_product_to_dict` | `src/widgets/product.py` | Used internally by `orm_order_to_dict` |
| `product_list_item_to_dict` | `src/widgets/product.py` | Used internally by `product_page_to_dict` |
| `product_page_to_dict` | `src/widgets/product.py` | Used by `FetchHandler.fetch_products()` |
| `dict_to_order_input` | `src/widgets/order.py` | Used by `save_orders()` in the order widget |
| `expense_to_dict` | `src/widgets/expense.py` | Used by `_ExpenseFetchHandler.fetch_expenses_for_month()` |
| `freight_result_to_dict` | `src/frontend/business.py` | Used by `distribute_freight()` in the business frontend |
| `xml_import_result_to_dict` | `src/frontend/business.py` | Used by `import_xml()` in the business frontend |

## Files to Create

**None.** No new files are needed — all functions are moved into existing modules.

## Files to Modify

### 1. `src/widgets/product.py`

**Current state:** Imports `product_page_to_dict, orm_order_to_dict` from `backend.utils.transformers`. Contains `FetchHandler` class with two methods that use these functions.

**Changes needed:**

1. **Remove the import line:**
   - Remove: `from backend.utils.transformers import product_page_to_dict, orm_order_to_dict`

2. **Add the following imports:**
   - `from backend.entities.orm import Product` (already available via the ORM, but needs explicit import for the new functions)
   - `from bridge import ProductDict, ProductListItemDict` (add `ProductListItemDict` to existing `bridge` imports)
   - `from backend.utils.currency import cents_to_display` (needed by `product_list_item_to_dict`)
   - `from backend.utils.date import datetime_to_br_date` (needed by `product_list_item_to_dict`)

3. **Add 4 new functions at module level** (after the `fetch_orders_for_month` public function, before any new public API if one is added):

   ```python
   def orm_product_to_dict(product: Product) -> ProductDict:
       """Transform an ORM Product entity into a bridge-compatible dict."""
       return {
           "id": product.ID,
           "name": product.NAME,
           "quantity": product.QUANTITY,
           "price": product.PRICE,
           "total": product.TOTAL_PRICE,
           "order_id": product.ORDER_ID,
           "itemOrdinal": product.ITEM_ORDINAL,
       }

   def orm_order_to_dict(order: Order) -> OrderDict:
       """Transform an ORM Order entity into a bridge-compatible dict."""
       return {
           "id": order.ID,
           "date": order.DATE.isoformat() if order.DATE else "",
           "supplier": order.SUPPLIER,
           "nfeKey": order.NFE_KEY or "",
           "freight": order.FREIGHT,
           "unloading": order.UNLOADING,
           "products": [orm_product_to_dict(p) for p in order.products],
       }

   def product_list_item_to_dict(product: Product) -> ProductListItemDict:
       """Transform an ORM Product entity into a dict for the widget bridge Product List table."""
       date_str = datetime_to_br_date(product.order.DATE) if product.order and product.order.DATE else ""
       return {
           "date": date_str,
           "supplier": product.order.SUPPLIER if product.order else "",
           "name": product.NAME,
           "price": cents_to_display(product.PRICE),
           "totalPrice": cents_to_display(product.TOTAL_PRICE),
           "orderId": product.ORDER_ID,
       }

   def product_page_to_dict(response: PageResponse[Product]) -> ProductPageResponseDict:
       """Transform a PageResponse[Product] into a bridge-compatible dict."""
       return {
           "items": [product_list_item_to_dict(p) for p in response.items],
           "page": response.page,
           "page_count": response.page_count,
           "total": response.total,
           "page_size": response.page_size,
       }
   ```

4. **Update `FetchHandler` methods** to reference the local functions directly (no import change needed since they'll be in the same module).

5. **Add `Order` to imports** from `backend.entities.orm` — currently only `Product` is implicitly available through the ORM relationship. The `orm_order_to_dict` function takes `Order` as a parameter, so `Order` must be imported.

**Rationale:** All 4 product-related transformations are tightly coupled to the product listing domain. They operate on `Product` and `Order` ORM entities and produce bridge dicts consumed by the product widget's `FetchHandler`.

---

### 2. `src/widgets/order.py`

**Current state:** Imports `dict_to_order_input` from `backend.utils.transformers`. Uses it in the `save_orders()` public function.

**Changes needed:**

1. **Remove the import line:**
   - Remove: `from backend.utils.transformers import dict_to_order_input`

2. **Add `dict_to_order_input` function** at module level (after the `_get_save_handler` function, before the public `save_orders` function):

   ```python
   def dict_to_order_input(d: OrderInputDict) -> OrderInput:
       """Transform a widget-bridge dict (from save/distribute/validate) into an OrderInput DTO."""
       products: list[OrderInput] = []
       for p in d.get("products", []):
           pi = OrderInput(
               id=p.get("id", ""),
               date="",
               supplier="",
               nfe_key="",
               freight=0,
               unloading=0,
               products=[],
           )
           pi.name = p.get("name", "")
           pi.quantity = p.get("quantity", 0)
           pi.price = p.get("price", 0)
           pi.total = p.get("total", 0)
           pi.order_id = p.get("order_id", "")
           pi.item_ordinal = p.get("itemOrdinal")
           products.append(pi)
       return OrderInput(
           id=d.get("id", ""),
           date=d.get("date", ""),
           supplier=d.get("supplier", ""),
           nfe_key=d.get("nfeKey", ""),
           freight=d.get("freight", 0),
           unloading=d.get("unloading", 0),
           products=products,
       )
   ```

3. The `save_orders()` function already calls `dict_to_order_input(o)` — no change to the call site needed.

**Rationale:** `dict_to_order_input` is exclusively used by the order save flow. It transforms UI bridge dicts into the `OrderInput` DTO that `SaveOrderService` expects.

---

### 3. `src/widgets/expense.py`

**Current state:** Imports `expense_to_dict` from `backend.utils.transformers`. Uses it in `_ExpenseFetchHandler.fetch_expenses_for_month()`.

**Changes needed:**

1. **Remove the import line:**
   - Remove: `from backend.utils.transformers import expense_to_dict`

2. **Add `expense_to_dict` function** at module level (inside the `_ExpenseFetchHandler` class or as a module-level helper — module-level is preferred for consistency):

   ```python
   def expense_to_dict(expense: Expense) -> ExpenseDict:
       """Transform an ORM Expense entity into a bridge-compatible dict."""
       return {
           "id": expense.ID,
           "month": expense.MONTH,
           "description": expense.DESCRIPTION,
           "value": expense.VALUE,
       }
   ```

3. **Add `Expense` to imports** from `backend.entities.orm` — currently not imported in this file.

4. The `_ExpenseFetchHandler.fetch_expenses_for_month()` method already calls `expense_to_dict(e)` — no change to the call site needed.

**Rationale:** `expense_to_dict` is exclusively used by the expense fetch flow.

---

### 4. `src/frontend/business.py`

**Current state:** Imports `dict_to_order_input`, `freight_result_to_dict`, `xml_import_result_to_dict` from `backend.utils.transformers`. Uses all three across `distribute_freight()`, `import_xml()`, and `validate_order()`.

**Changes needed:**

1. **Remove the import block:**
   ```python
   from backend.utils.transformers import (
       dict_to_order_input,
       freight_result_to_dict,
       xml_import_result_to_dict,
   )
   ```

2. **Add a local import** for `dict_to_order_input` from the order widget:
   ```python
   from widgets.order import dict_to_order_input
   ```

3. **Add `freight_result_to_dict` function** at module level:

   ```python
   def freight_result_to_dict(result: FreightDistributionResult) -> FreightResultDict:
       """Transform a FreightDistributionResult into a bridge-compatible dict."""
       return {
           "order_id": result.order_id,
           "old_freight": result.old_freight,
           "old_unloading": result.old_unloading,
           "ratio": result.ratio,
           "products_total_before": result.products_total_before,
           "products_total_after": result.products_total_after,
           "new_products": [
               {
                   "id": p.id,
                   "name": p.name,
                   "quantity": p.quantity,
                   "price": p.price,
                   "total": p.total,
                   "order_id": p.order_id,
                   "itemOrdinal": p.item_ordinal,
               }
               for p in result.new_products
           ],
       }
   ```

4. **Add `xml_import_result_to_dict` function** at module level:

   ```python
   def xml_import_result_to_dict(result: XmlImportResult) -> XmlImportResultDict:
       """Transform an XmlImportResult into a bridge-compatible dict."""
       return {
           "orders": [
               {
                   "id": o.id,
                   "date": o.date,
                   "supplier": o.supplier,
                   "nfeKey": o.nfe_key,
                   "freight": o.freight,
                   "unloading": o.unloading,
                   "products": [
                       {
                           "id": p.id,
                           "name": p.name,
                           "quantity": p.quantity,
                           "price": p.price,
                           "total": p.total,
                           "order_id": p.order_id,
                           "itemOrdinal": p.item_ordinal,
                       }
                       for p in o.products
                   ],
               }
               for o in result.orders
           ],
           "warnings": result.warnings,
       }
   ```

**Rationale:** `freight_result_to_dict` and `xml_import_result_to_dict` are exclusively used in the business frontend (`business.py`). They transform service-layer result objects into bridge dicts consumed by the frontend. `dict_to_order_input` is also used here (in `distribute_freight()` and `validate_order()`), but since it logically belongs to the order domain, we import it from `widgets.order` rather than duplicating it.

---

### 5. `src/backend/utils/__init__.py`

**Current state:** Re-exports all 8 transformer functions from `transformers.py` plus utility functions.

**Changes needed:**

1. **Remove the transformer import block:**
   ```python
   from .transformers import (
       dict_to_order_input,
       expense_to_dict,
       freight_result_to_dict,
       orm_order_to_dict,
       orm_product_to_dict,
       product_list_item_to_dict,
       product_page_to_dict,
       xml_import_result_to_dict,
   )
   ```

2. **Remove all 8 transformer names from `__all__`:**
   ```python
   # Remove these lines from __all__:
   "dict_to_order_input",
   "expense_to_dict",
   "freight_result_to_dict",
   "orm_order_to_dict",
   "orm_product_to_dict",
   "product_list_item_to_dict",
   "product_page_to_dict",
   "xml_import_result_to_dict",
   ```

**Rationale:** After the transformer functions are removed from `transformers.py`, these re-exports would break. The `__init__.py` should only export the remaining utility functions (`cents_to_display`, `parse_currency_to_cents`, `parse_month_for_orders`, `parse_month_for_expenses`, `br_date_to_iso`, `iso_to_br_date`, `current_month_orders`, `current_month_expenses`, `format_time_now`, `normalize_text`).

---

### 6. `src/backend/utils/transformers.py`

**Action:** **Delete this file entirely.**

**Reason:** All 8 functions have been moved to their respective domain modules. No other file depends on this module.

---

## Files to Delete

- **`src/backend/utils/transformers.py`** — All functions moved to domain modules.

## Files to Keep (No Changes)

| File | Reason |
|---|---|
| `src/bridge/__init__.py` | TypedDict definitions are shared contracts, not transformation logic. They stay in the bridge module. |
| `src/backend/entities/orm.py` | ORM entity definitions — untouched. |
| `src/backend/models/dto.py` | DTO definitions — untouched. |
| `src/backend/services/freight_distribution.py` | Service logic — untouched (only the result type is consumed by `freight_result_to_dict`). |
| `src/backend/services/xml_import_service.py` | Service logic — untouched (only the result type is consumed by `xml_import_result_to_dict`). |
| `src/backend/utils/currency.py` | Utility functions — untouched. |
| `src/backend/utils/date.py` | Utility functions — untouched. |
| `src/backend/utils/text.py` | Utility functions — untouched. |

---

## Import Migration Table

| File | Old Import | New Import(s) |
|---|---|---|
| `src/widgets/product.py` | `from backend.utils.transformers import product_page_to_dict, orm_order_to_dict` | `from backend.entities.orm import Order, Product`<br>`from bridge import ProductDict, ProductListItemDict`<br>`from backend.utils.currency import cents_to_display`<br>`from backend.utils.date import datetime_to_br_date` |
| `src/widgets/order.py` | `from backend.utils.transformers import dict_to_order_input` | _(no import needed — function defined locally)_ |
| `src/widgets/expense.py` | `from backend.utils.transformers import expense_to_dict` | `from backend.entities.orm import Expense`<br>_(function defined locally)_ |
| `src/frontend/business.py` | `from backend.utils.transformers import dict_to_order_input, freight_result_to_dict, xml_import_result_to_dict` | `from widgets.order import dict_to_order_input`<br>_(freight_result_to_dict and xml_import_result_to_dict defined locally)_ |
| `src/backend/utils/__init__.py` | `from .transformers import (...)` | _(removed)_ |

---

## Detailed File-by-File Changes

### `src/widgets/product.py` — Full change summary

**Imports to add:**
```python
from backend.entities.orm import Order, Product  # Product already imported indirectly; make explicit
from bridge import ProductDict, ProductListItemDict  # Add ProductListItemDict
from backend.utils.currency import cents_to_display
from backend.utils.date import datetime_to_br_date
```

**Imports to remove:**
```python
from backend.utils.transformers import product_page_to_dict, orm_order_to_dict
```

**Functions to add (4):** `orm_product_to_dict`, `orm_order_to_dict`, `product_list_item_to_dict`, `product_page_to_dict`

**Methods to update:** None — `FetchHandler` methods already call the functions by name; once the functions are local, the calls resolve automatically.

---

### `src/widgets/order.py` — Full change summary

**Imports to remove:**
```python
from backend.utils.transformers import dict_to_order_input
```

**Functions to add (1):** `dict_to_order_input`

**Functions to update:** None — `save_orders()` already calls `dict_to_order_input(o)` by name.

---

### `src/widgets/expense.py` — Full change summary

**Imports to add:**
```python
from backend.entities.orm import Expense
```

**Imports to remove:**
```python
from backend.utils.transformers import expense_to_dict
```

**Functions to add (1):** `expense_to_dict`

**Methods to update:** None — `_ExpenseFetchHandler.fetch_expenses_for_month()` already calls `expense_to_dict(e)` by name.

---

### `src/frontend/business.py` — Full change summary

**Imports to remove:**
```python
from backend.utils.transformers import (
    dict_to_order_input,
    freight_result_to_dict,
    xml_import_result_to_dict,
)
```

**Imports to add:**
```python
from widgets.order import dict_to_order_input
```

**Functions to add (2):** `freight_result_to_dict`, `xml_import_result_to_dict`

**Functions to update:** None — call sites already reference the functions by name; the local definitions resolve automatically.

---

### `src/backend/utils/__init__.py` — Full change summary

**Remove the transformer import block** (lines 4–13) and **remove the 8 transformer names from `__all__`** (lines 26–33).

**Resulting `__init__.py` content:**
```python
from .currency import cents_to_display, parse_currency_to_cents
from .date import parse_month_for_orders, parse_month_for_expenses, br_date_to_iso, iso_to_br_date, current_month_orders, current_month_expenses, format_time_now
from .text import normalize_text

__all__ = [
    "cents_to_display",
    "parse_currency_to_cents",
    "parse_month_for_orders",
    "parse_month_for_expenses",
    "br_date_to_iso",
    "iso_to_br_date",
    "current_month_orders",
    "current_month_expenses",
    "format_time_now",
    "normalize_text",
]
```

---

## Verification Steps

1. **Run the app** to verify all imports resolve and the UI loads correctly:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   python src/main.py
   ```
   - Verify the main window opens.
   - Verify the product list loads data (if the DB has data).
   - Verify navigation between sections works.
   - Test the freight distribution flow (open an order, distribute freight, verify result).
   - Test the XML import flow (import an NFe XML file, verify result).
   - Test saving orders and expenses.

2. **Run qmllint** (no QML files are changed, but verify nothing broke):
   ```powershell
   .\.venv\Scripts\Activate.ps1
   & ".venv\Lib\site-packages\PySide6\qmllint.exe" -I . App\*.qml
   ```

3. **Verify no dangling imports** — search the entire `src/` directory for any remaining references to `transformers`:
   ```powershell
   rg "transformers" src/
   ```
   Expected: No matches (the file should be deleted).

4. **Verify `backend.utils` re-exports** — confirm the `__init__.py` no longer exports transformer functions:
   ```python
   from backend.utils import dict_to_order_input  # Should raise ImportError
   ```

5. **Verify cross-module import** — confirm `business.py` can import `dict_to_order_input` from `widgets.order`:
   ```python
   from widgets.order import dict_to_order_input  # Should succeed
   ```

---

## Risks and Considerations

### 1. Circular Import Risk
- **Risk:** `src/frontend/business.py` imports from `src/widgets/order.py`. If `src/widgets/order.py` ever imports from `src/frontend/`, a circular import would occur.
- **Mitigation:** Currently `widgets.order` does NOT import from `frontend`. The import direction is `frontend → widgets`, which is safe. Document this dependency direction for future development.

### 2. `datetime_to_br_date` parameter type
- **Note:** `product_list_item_to_dict` calls `datetime_to_br_date(product.order.DATE)`. The `product.order.DATE` is of type `date` (from SQLAlchemy `Mapped[date]`), but `datetime_to_br_date` expects a `datetime` object (per the signature in `date.py`). This is a pre-existing potential runtime issue — `date` is a subclass of `object` but not `datetime`. In practice, SQLAlchemy may return a `datetime` object when the column is `DateTime`, or a `date` when the column is `Date`. The Order.DATE column is `Date`, so `product.order.DATE` is a `date` object. The `datetime_to_br_date` function calls `date.strftime()`, which works on both `date` and `datetime` since `strftime` is available on both. **No change needed** — this is safe.

### 3. No `transformers.py` file left behind
- After deletion, there should be no `transformers.py` file, no `__pycache__` entries, and no imports referencing it. The `rm` / delete operation should be thorough.

### 4. Bridge TypedDict comments
- The TypedDict docstrings in `src/bridge/__init__.py` reference the transformer function names (e.g., `"from orm_order_to_dict"`). These comments are documentation and should be updated to reflect the new locations, but they are not functional. Update them as a cosmetic improvement:
  - `ProductListItemDict`: Change `"from product_page_to_dict / ORM transform"` → `"from product_list_item_to_dict"`
  - `ProductDict`: Change `"from orm_product_to_dict"` → no change needed (still accurate)
  - `OrderDict`: Change `"from orm_order_to_dict"` → no change needed (still accurate)
  - `ExpenseDict`: Change `"from expense_to_dict"` → no change needed (still accurate)

### 5. Backward compatibility
- No other code outside the 4 modified files imports from `transformers.py`. The `backend.utils.__init__.py` re-exports are the only indirect dependency, and those are removed in this plan. There are **no breaking changes to public APIs** — the `widgets/__init__.py` already exports only the public functions (`fetch_products`, `save_orders`, etc.), not the transformer helpers.

### 6. Internal function dependencies
- `orm_order_to_dict` calls `orm_product_to_dict` internally.
- `product_page_to_dict` calls `product_list_item_to_dict` internally.
- Both pairs move to the same file (`product.py`), so no cross-file dependencies are introduced.

---

## Implementation Order

Suggested sequence to minimize risk and maintain a working state at each step:

1. **Modify `src/widgets/product.py`** — Add the 4 product transformer functions, update imports.
2. **Modify `src/widgets/order.py`** — Add `dict_to_order_input`, remove transformer import.
3. **Modify `src/widgets/expense.py`** — Add `expense_to_dict`, remove transformer import, add `Expense` import.
4. **Modify `src/frontend/business.py`** — Add `freight_result_to_dict` and `xml_import_result_to_dict`, replace transformer imports with local + `widgets.order` import.
5. **Modify `src/backend/utils/__init__.py`** — Remove transformer re-exports.
6. **Delete `src/backend/utils/transformers.py`** — Final cleanup.
7. **Verify** — Run the app, check for dangling imports, test all flows.

This order ensures that each domain module has its functions defined *before* any other module tries to import them. Step 4 (business.py) depends on step 2 (order.py) because business.py imports `dict_to_order_input` from `widgets.order`. Steps 1 and 3 are independent of each other and of step 4.
