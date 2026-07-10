# Implementation Plan: Merge api/ into qml_backend and Propose Multi-File Split

## Summary

This plan has two phases: (1) inline the five API wrapper functions from `src/backend/api/` directly into `BackendManager` in `qml_backend.py`, eliminating the `call_with_injection` DI-wrapper pattern and deleting the `api/` directory; (2) split the resulting (still monolithic) `qml_backend.py` into five well-organized files based on logical responsibility groupings, preserving the exact QML-facing interface.

---

## Part 1 — Merge `api/` into `qml_backend.py`

### 1.1. What the `api/` layer currently does

Each file in `api/` contains:
1. A **pure function** that accepts a `session_factory` or service instance as an explicit parameter.
2. An **injected wrapper** that calls `call_with_injection()` to resolve those parameters from the DI container.
3. A **getter function** (`get_*_injected()`) that returns the injected wrapper for import by `qml_backend.py`.

**Example from `orders.py`:**
```
orders_for_month(month, session_factory)  → pure function
_orders_for_month_injected(month)         → wraps with call_with_injection
get_orders_for_month_injected()           → returns the wrapper
```

### 1.2. Why this layer is redundant now

`qml_backend.py` already:
- Creates the injector in `__init__`
- Resolves `self._session_factory` and `self._save_order_service` / `self._save_expense_service` directly
- Only uses the api layer to call repository/service methods

The `call_with_injection` indirection exists to let standalone functions access the DI container, but `BackendManager` already *is* the composition root — it holds the resolved dependencies. The api layer adds zero value beyond a function-call indirection.

### 1.3. Mapping: api functions → inline methods on BackendManager

| api file | api function | → New inline method on BackendManager |
|---|---|---|
| `orders.py` | `orders_for_month(month, session_factory)` | `_fetch_orders_for_month(month: str) -> list[Order]` |
| `orders.py` | `product_list(page, supplier, product, month, session_factory)` | `_fetch_products(page, supplier, product, month) -> PageResponse[Product]` |
| `save_expenses.py` | `expenses_for_month(month, session_factory)` | `_fetch_expenses_for_month(month: str) -> list[Expense]` |
| `save_expenses.py` | `save_expenses(expenses, month, service)` | `_save_expenses(expenses: list[ExpenseInput], month: str) -> None` |
| `save_orders.py` | `save_orders(orders, deleted_orders, service)` | `_save_orders(orders: list[OrderInput], deleted_orders: list[str]) -> None` |

### 1.4. Changes to `qml_backend.py` — Part 1 (merge)

#### Imports to remove:
- `from backend.api.orders import get_orders_for_month_injected, get_product_list_injected`
- `from backend.api.save_expenses import get_expenses_for_month_injected, get_save_expenses_injected`
- `from backend.api.save_orders import get_save_orders_injected`

#### Imports to add:
- `from backend.repositories.order_repository import OrderRepository`
- `from backend.repositories.expense_repository import ExpenseRepository`
- `from backend.utils.date import parse_month_for_orders, parse_month_for_expenses`
- `from backend.entities.orm import Order, Product, Expense`

#### `__init__` changes:
- **Remove** all `from backend.api.* import get_*_injected` lines
- **Remove** all `self._orders_for_month_fn = ...`, `self._product_list_fn = ...`, etc. assignments
- Keep existing `self._session_factory`, `self._save_order_service`, `self._save_expense_service`
- Keep existing `self._validation`, `self._freight`, `self._xml_import`

#### New private methods to add (before the public `@Slot` methods):

```python
def _fetch_orders_for_month(self, month: str) -> list[Order]:
    """Fetch ORM Order entities with products for a given MM/yyyy month."""
    m, y = parse_month_for_orders(month)
    with self._session_factory() as session:
        return OrderRepository(session).fetch_orders_for_month(month=m, year=y)

def _fetch_products(
    self,
    page: int,
    supplier: str | None = None,
    product: str | None = None,
    month: str | None = None,
) -> PageResponse[Product]:
    """Fetch paginated product search results."""
    with self._session_factory() as session:
        return OrderRepository(session).search_products(
            page=page, supplier=supplier, product=product, month=month,
        )

def _fetch_expenses_for_month(self, month: str) -> list[Expense]:
    """Fetch ORM Expense entities for a given YYYY-MM month."""
    validated = parse_month_for_expenses(month)
    with self._session_factory() as session:
        return ExpenseRepository(session).fetch_expenses_for_month(month=validated)

def _save_orders(self, orders: list[OrderInput], deleted_orders: list[str]) -> None:
    """Delegate to SaveOrderService."""
    self._save_order_service.save_orders(orders=orders, deleted_order_ids=deleted_orders)

def _save_expenses(self, expenses: list[ExpenseInput], month: str) -> None:
    """Delegate to SaveExpenseService."""
    validated = parse_month_for_expenses(month)
    self._save_expense_service.save_expenses(expenses=expenses, month=validated)
```

#### Public `@Slot` methods — update body to call new private methods:

- `orders_for_month(month)` → call `self._fetch_orders_for_month(month)` instead of `self._orders_for_month_fn(month)`
- `product_list(page, supplier, product, month)` → call `self._fetch_products(...)` instead of `self._product_list_fn(...)`
- `expenses_for_month(month)` → call `self._fetch_expenses_for_month(month)` instead of `self._expenses_for_month_fn(month)`
- `save_orders(orders, deleted_orders)` → call `self._save_orders_fn(...)` → `self._save_orders(...)`
- `save_expenses(expenses, month)` → call `self._save_expenses_fn(...)` → `self._save_expenses(...)`

**No changes to signatures, `@Slot` decorators, signal emissions, error handling, or return shapes.**

### 1.5. Changes to `src/backend/__init__.py`

- **Remove** these lines:
  ```python
  from .api.orders import orders_for_month, product_list
  from .api.save_orders import save_orders
  from .api.save_expenses import expenses_for_month, save_expenses
  ```
- **Remove** from `__all__`: `"orders_for_month"`, `"product_list"`, `"save_orders"`, `"expenses_for_month"`, `"save_expenses"`

### 1.6. Changes to `src/backend/qml_models.py`

This file imports from `api/` at the top level and inside a method:
```python
from backend.api.orders import orders_for_month   # top-level import
from backend.api.save_expenses import expenses_for_month  # inside ExpenseListModel.load_for_month
```

**Replace with:**
- Import `BackendManager` from `backend.qml_backend` and call methods through the singleton instance.
- **OR** — simpler approach: import `OrderRepository` and `ExpenseRepository` directly with a session factory.

**Recommended approach:** Create a module-level helper in `qml_models.py` that creates a temporary `BackendManager` instance or reuses the existing one. Since `qml_models.py` is used by QML models that may already have access to the `BackendManager` context property, the cleanest approach is:

```python
# Replace top-level import
from backend.qml_backend import BackendManager

# In OrderListModel.load_for_month:
# Use the shared BackendManager instance (already registered as context property in main.py)
# But since QAbstractListModel methods run synchronously, we need a backend instance.
# Solution: import the session factory directly.
from backend.injector_module import get_injector
from backend.repositories.order_repository import OrderRepository
```

**Actually, the simplest migration:** Since `qml_models.py` is a separate file that creates its own data models, and `BackendManager` creates its own injector, we should:

1. In `qml_models.py`, replace `from backend.api.orders import orders_for_month` with a direct call pattern:
   ```python
   from backend.injector_module import get_injector
   from backend.repositories.order_repository import OrderRepository
   from backend.utils.date import parse_month_for_orders
   ```
2. In `load_for_month`:
   ```python
   injector = get_injector()
   session_factory = injector.get(Callable[[], Session])
   m, y = parse_month_for_orders(month)
   with session_factory() as session:
       raw_orders = OrderRepository(session).fetch_orders_for_month(month=m, year=y)
   ```
3. Similarly for `ExpenseListModel.load_for_month`, replace the inline import.

**Alternative (cleaner):** Have `qml_models.py` accept a `BackendManager` instance or session factory via constructor. But this requires QML-side changes. The simplest no-breaking-change approach is direct repository access with the shared injector (same injector singleton, same engine).

### 1.7. Delete the `api/` directory

After verifying all references are removed:
- Delete `src/backend/api/__init__.py`
- Delete `src/backend/api/orders.py`
- Delete `src/backend/api/save_expenses.py`
- Delete `src/backend/api/save_orders.py`
- Delete `src/backend/api/__pycache__/` (automatically via git clean or manually)

---

## Part 2 — Split `qml_backend.py` into Multiple Files

### 2.1. Analysis of current `qml_backend.py` (367 lines)

The file contains three distinct concerns:
1. **Composition root** — `__init__`, signals, dependency resolution (~30 lines)
2. **Data-fetch `@Slot` methods** — `orders_for_month`, `product_list`, `expenses_for_month` (~50 lines)
3. **Save `@Slot` methods** — `save_orders`, `save_expenses` (~40 lines)
4. **Business logic `@Slot` methods** — `distribute_freight`, `import_xml`, `validate_order`, `validate_expense` (~70 lines)
5. **DTO/ORM transformation logic** — repeated inline code that converts `dict` → `OrderInput` and `Order` → `dict` (~80 lines, scattered across methods)

### 2.2. Proposed file split

```
src/backend/
├── qml_backend.py           (~40 lines)  — BackendManager class: signals, __init__, @Slot dispatch
├── qml_transformers.py      (~80 lines)  — DTO/ORM transformation helpers
├── qml_fetch.py             (~60 lines)  — Data fetch private methods + their @Slot wrappers
├── qml_save.py              (~50 lines)  — Save private methods + their @Slot wrappers
└── qml_business.py          (~80 lines)  — Business logic private methods + their @Slot wrappers
```

**Total: ~310 lines** (down from 367, due to deduplication and cleaner structure)

### 2.3. File-by-file responsibilities

#### `src/backend/qml_backend.py` (~40 lines)

**Purpose:** Composition root and QML facade. This is the file that `main.py` imports.

**Contents:**
- `BackendManager` class definition
- Signal declarations: `data_changed`, `save_completed`, `error_occurred`
- `__init__`: create injector, resolve dependencies, instantiate sub-objects
- Import and delegate to sub-modules

**Pattern:** The class holds references to handler modules and delegates `@Slot` calls to them. This keeps the class itself minimal.

```python
class BackendManager(QObject):
    data_changed = Signal()
    save_completed = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # ... resolve DI ...
        self._fetch_handler = FetchHandler(self._session_factory, self._validation)
        self._save_handler = SaveHandler(self._save_order_service, self._save_expense_service)
        self._business_handler = BusinessHandler(self._validation, self._freight, self._xml_import)

    # @Slot methods that delegate:
    @Slot(str)
    def orders_for_month(self, month: str) -> list[dict[str, Any]]:
        return self._fetch_handler.orders_for_month(month)

    @Slot(int, str, str, str)
    def product_list(self, page: int, supplier: str, product: str, month: str) -> dict[str, Any]:
        return self._fetch_handler.product_list(page, supplier, product, month)

    # ... etc, one delegate per @Slot ...
```

#### `src/backend/qml_transformers.py` (~80 lines)

**Purpose:** Shared transformation functions used across all handler modules. Eliminates the duplicated `OrderInput` construction and `dict`-to-`Order` conversion code.

**Contents:**

```python
def orm_order_to_dict(order: Order) -> dict[str, Any]:
    """Transform an ORM Order entity into a QML-compatible dict."""
    return {
        "id": order.ID,
        "date": order.DATE.isoformat() if order.DATE else "",
        "supplier": order.SUPPLIER,
        "nfeKey": order.NFE_KEY or "",
        "freight": order.FREIGHT,
        "unloading": order.UNLOADING,
        "products": [orm_product_to_dict(p) for p in order.products],
    }

def orm_product_to_dict(product: Product) -> dict[str, Any]:
    """Transform an ORM Product entity into a QML-compatible dict."""
    return {
        "id": product.ID,
        "name": product.NAME,
        "quantity": product.QUANTITY,
        "price": product.PRICE,
        "total": product.TOTAL_PRICE,
        "order_id": product.ORDER_ID,
        "itemOrdinal": product.ITEM_ORDINAL,
    }

def dict_to_order_input(d: dict[str, Any]) -> OrderInput:
    """Transform a QML dict (from save/distribute/validate) into an OrderInput DTO."""
    products: list[OrderInput] = []
    for p in d.get("products", []):
        pi = OrderInput(
            id=p.get("id", ""), date="", supplier="", nfe_key="",
            freight=0, unloading=0, products=[],
        )
        pi.name = p.get("name", "")
        pi.quantity = p.get("quantity", 0)
        pi.price = p.get("price", 0)
        pi.total = p.get("total", 0)
        pi.order_id = p.get("order_id", "")
        pi.item_ordinal = p.get("itemOrdinal")
        products.append(pi)
    return OrderInput(
        id=d.get("id", ""), date=d.get("date", ""),
        supplier=d.get("supplier", ""), nfe_key=d.get("nfeKey", ""),
        freight=d.get("freight", 0), unloading=d.get("unloading", 0),
        products=products,
    )

def expense_to_dict(expense: Expense) -> dict[str, Any]:
    """Transform an ORM Expense entity into a QML-compatible dict."""
    return {
        "id": expense.ID,
        "month": expense.MONTH,
        "description": expense.DESCRIPTION,
        "value": expense.VALUE,
    }

def product_page_to_dict(response: PageResponse[Product]) -> dict[str, Any]:
    """Transform a PageResponse[Product] into a QML-compatible dict."""
    return {
        "items": [orm_product_to_dict(p) for p in response.items],
        "page": response.page,
        "page_count": response.page_count,
        "total": response.total,
        "page_size": response.page_size,
    }

def freight_result_to_dict(result: FreightDistributionResult) -> dict[str, Any]:
    """Transform a FreightDistributionResult into a QML-compatible dict."""
    return {
        "order_id": result.order_id,
        "old_freight": result.old_freight,
        "old_unloading": result.old_unloading,
        "ratio": result.ratio,
        "products_total_before": result.products_total_before,
        "products_total_after": result.products_total_after,
        "new_products": [orm_product_to_dict(p) for p in result.new_products],
    }

def xml_import_result_to_dict(result: XmlImportResult) -> dict[str, Any]:
    """Transform an XmlImportResult into a QML-compatible dict."""
    return {
        "orders": [
            {
                "id": o.id, "date": o.date, "supplier": o.supplier,
                "nfeKey": o.nfe_key, "freight": o.freight, "unloading": o.unloading,
                "products": [
                    {"id": p.id, "name": p.name, "quantity": p.quantity,
                     "price": p.price, "total": p.total,
                     "order_id": p.order_id, "itemOrdinal": p.item_ordinal}
                    for p in o.products
                ],
            }
            for o in result.orders
        ],
        "warnings": result.warnings,
    }
```

#### `src/backend/qml_fetch.py` (~60 lines)

**Purpose:** Data-fetch logic. Contains the private fetch methods and their `@Slot`-wrapped public methods.

**Contents:**

```python
class FetchHandler:
    def __init__(self, session_factory: Callable[[], Session], validation: ValidationService) -> None:
        self._session_factory = session_factory
        self._validation = validation

    def fetch_orders_for_month(self, month: str) -> list[Order]:
        m, y = parse_month_for_orders(month)
        with self._session_factory() as session:
            return OrderRepository(session).fetch_orders_for_month(month=m, year=y)

    def fetch_products(
        self, page: int, supplier: str | None, product: str | None, month: str | None,
    ) -> PageResponse[Product]:
        with self._session_factory() as session:
            return OrderRepository(session).search_products(
                page=page, supplier=supplier, product=product, month=month,
            )

    def fetch_expenses_for_month(self, month: str) -> list[Expense]:
        validated = parse_month_for_expenses(month)
        with self._session_factory() as session:
            return ExpenseRepository(session).fetch_expenses_for_month(month=validated)
```

The `BackendManager`'s `@Slot` methods for fetch will call these and apply transformers + error handling + signal emission.

#### `src/backend/qml_save.py` (~50 lines)

**Purpose:** Save logic.

**Contents:**

```python
class SaveHandler:
    def __init__(self, save_order_service: SaveOrderService, save_expense_service: SaveExpenseService) -> None:
        self._save_order_service = save_order_service
        self._save_expense_service = save_expense_service

    def save_orders(self, orders: list[OrderInput], deleted_orders: list[str]) -> None:
        self._save_order_service.save_orders(orders=orders, deleted_order_ids=deleted_orders)

    def save_expenses(self, expenses: list[ExpenseInput], month: str) -> None:
        validated = parse_month_for_expenses(month)
        self._save_expense_service.save_expenses(expenses=expenses, month=validated)
```

#### `src/backend/qml_business.py` (~80 lines)

**Purpose:** Business logic methods.

**Contents:**

```python
class BusinessHandler:
    def __init__(
        self,
        validation: ValidationService,
        freight: FreightDistributionService,
        xml_import: XmlImportService,
    ) -> None:
        self._validation = validation
        self._freight = freight
        self._xml_import = xml_import

    def distribute_freight(self, order_input: OrderInput) -> FreightDistributionResult:
        return self._freight.distribute(order_input)

    def import_xml(self, file_path: str) -> XmlImportResult:
        return self._xml_import.parse_file(file_path)

    def validate_order(self, order_input: OrderInput) -> ValidationResult:
        return self._validation.validate_order(order_input)

    def validate_expense(self, description: str, value: int) -> ValidationResult:
        return self._validation.validate_expense(description, value)
```

### 2.4. Import graph

```
qml_backend.py          ← main.py imports BackendManager here
    ├── qml_transformers.py   ← imported by all handler modules
    ├── qml_fetch.py          ← imported by qml_backend.py
    ├── qml_save.py           ← imported by qml_backend.py
    └── qml_business.py       ← imported by qml_backend.py
```

**Dependencies:**
- `qml_fetch.py` imports: `OrderRepository`, `ExpenseRepository`, `parse_month_for_orders`, `parse_month_for_expenses`, `Order`, `Product`, `Expense`, `PageResponse`
- `qml_save.py` imports: `SaveOrderService`, `SaveExpenseService`, `parse_month_for_expenses`, `ExpenseInput`
- `qml_business.py` imports: `ValidationService`, `FreightDistributionService`, `XmlImportService`, `OrderInput`
- `qml_transformers.py` imports: `Order`, `Product`, `Expense`, `OrderInput`, `ProductInput`, `PageResponse`, `FreightDistributionResult`, `XmlImportResult`
- `qml_backend.py` imports: all four handler modules + `qml_transformers`

### 2.5. Why this split works

1. **Single responsibility:** Each handler module owns one concern (fetch, save, business logic).
2. **No circular imports:** `qml_backend.py` is the root; all handlers import from it only for DI (or receive dependencies via constructor). Transformers are leaf modules.
3. **Preserves QML interface:** The `@Slot` signatures, signal names, and return shapes remain identical. Only the internal delegation changes.
4. **Testable:** Each handler class can be unit-tested independently with mock dependencies.
5. **Extensible:** Adding a new `@Slot` method is a matter of adding to one handler file.

---

## Part 3 — File-by-File Implementation Steps

### Phase 1: Merge api/ into qml_backend

#### Step 1: Update `qml_backend.py` — remove api imports, add repository imports

**File:** `src/backend/qml_backend.py`

1. Remove these import lines:
   ```python
   from backend.api.orders import get_orders_for_month_injected, get_product_list_injected
   from backend.api.save_expenses import get_expenses_for_month_injected, get_save_expenses_injected
   from backend.api.save_orders import get_save_orders_injected
   ```

2. Add these import lines (in the existing import block):
   ```python
   from backend.repositories.order_repository import OrderRepository
   from backend.repositories.expense_repository import ExpenseRepository
   from backend.utils.date import parse_month_for_orders, parse_month_for_expenses
   from backend.entities.orm import Order, Product, Expense
   ```

#### Step 2: Update `__init__` — remove api function assignments

**File:** `src/backend/qml_backend.py`

Remove these lines from `__init__`:
```python
from backend.api.orders import get_orders_for_month_injected, get_product_list_injected
from backend.api.save_expenses import get_expenses_for_month_injected, get_save_expenses_injected
from backend.api.save_orders import get_save_orders_injected
self._orders_for_month_fn = get_orders_for_month_injected()
self._product_list_fn = get_product_list_injected()
self._expenses_for_month_fn = get_expenses_for_month_injected()
self._save_orders_fn = get_save_orders_injected()
self._save_expenses_fn = get_save_expenses_injected()
```

Keep all the `self._injector`, `self._session_factory`, `self._save_order_service`, `self._save_expense_service`, `self._validation`, `self._freight`, `self._xml_import` lines.

#### Step 3: Add private fetch/save methods

**File:** `src/backend/qml_backend.py`

Add these five methods **before** the `@Slot` public methods (after `__init__`):

```python
def _fetch_orders_for_month(self, month: str) -> list[Order]:
    m, y = parse_month_for_orders(month)
    with self._session_factory() as session:
        return OrderRepository(session).fetch_orders_for_month(month=m, year=y)

def _fetch_products(
    self,
    page: int,
    supplier: str | None = None,
    product: str | None = None,
    month: str | None = None,
) -> PageResponse[Product]:
    with self._session_factory() as session:
        return OrderRepository(session).search_products(
            page=page, supplier=supplier, product=product, month=month,
        )

def _fetch_expenses_for_month(self, month: str) -> list[Expense]:
    validated = parse_month_for_expenses(month)
    with self._session_factory() as session:
        return ExpenseRepository(session).fetch_expenses_for_month(month=validated)

def _save_orders(self, orders: list[OrderInput], deleted_orders: list[str]) -> None:
    self._save_order_service.save_orders(orders=orders, deleted_order_ids=deleted_orders)

def _save_expenses(self, expenses: list[ExpenseInput], month: str) -> None:
    validated = parse_month_for_expenses(month)
    self._save_expense_service.save_expenses(expenses=expenses, month=validated)
```

#### Step 4: Update public `@Slot` methods to use new private methods

**File:** `src/backend/qml_backend.py`

Update each public method body:

- **`orders_for_month`**: Replace `self._orders_for_month_fn(month)` → `self._fetch_orders_for_month(month)`. The rest of the method (ORM→dict transformation, signal emission, error handling) stays identical.

- **`product_list`**: Replace `self._product_list_fn(...)` → `self._fetch_products(...)`. The rest stays identical.

- **`expenses_for_month`**: Replace `self._expenses_for_month_fn(month)` → `self._fetch_expenses_for_month(month)`. The rest stays identical.

- **`save_orders`**: Replace `self._save_orders_fn(final_orders, deleted_orders)` → `self._save_orders(final_orders, deleted_orders)`. The rest (dict→OrderInput conversion, signal emission, error handling) stays identical.

- **`save_expenses`**: Replace `self._save_expenses_fn(expense_inputs, month)` → `self._save_expenses(expense_inputs, month)`. The rest stays identical.

#### Step 5: Update `src/backend/__init__.py`

**File:** `src/backend/__init__.py`

1. Remove these three import lines:
   ```python
   from .api.orders import orders_for_month, product_list
   from .api.save_orders import save_orders
   from .api.save_expenses import expenses_for_month, save_expenses
   ```

2. Remove these five entries from `__all__`:
   ```
   "orders_for_month",
   "product_list",
   "save_orders",
   "expenses_for_month",
   "save_expenses",
   ```

#### Step 6: Update `src/backend/qml_models.py`

**File:** `src/backend/qml_models.py`

1. Replace top-level import:
   ```python
   # OLD:
   from backend.api.orders import orders_for_month
   # NEW:
   from backend.injector_module import get_injector
   from backend.repositories.order_repository import OrderRepository
   from backend.utils.date import parse_month_for_orders
   from sqlalchemy.orm import Session
   from typing import Callable
   ```

2. Update `OrderListModel.load_for_month`:
   ```python
   # OLD:
   raw_orders = orders_for_month(month)
   # NEW:
   injector = get_injector()
   session_factory = injector.get(Callable[[], Session])
   m, y = parse_month_for_orders(month)
   with session_factory() as session:
       raw_orders = OrderRepository(session).fetch_orders_for_month(month=m, year=y)
   ```

3. Update `ExpenseListModel.load_for_month`:
   ```python
   # OLD (inline import):
   from backend.api.save_expenses import expenses_for_month
   raw_expenses = expenses_for_month(month)
   # NEW:
   from backend.injector_module import get_injector
   from backend.repositories.expense_repository import ExpenseRepository
   from backend.utils.date import parse_month_for_expenses
   injector = get_injector()
   session_factory = injector.get(Callable[[], Session])
   validated = parse_month_for_expenses(month)
   with session_factory() as session:
       raw_expenses = ExpenseRepository(session).fetch_expenses_for_month(month=validated)
   ```

#### Step 7: Delete the `api/` directory

**Files to delete:**
- `src/backend/api/__init__.py`
- `src/backend/api/orders.py`
- `src/backend/api/save_expenses.py`
- `src/backend/api/save_orders.py`

**Verify first:** Run a grep to confirm no remaining references:
```powershell
grep -r "backend.api" src/
```
Should return zero results. If any appear, update them first.

#### Step 8: Verify the app runs

```powershell
.\.venv\Scripts\Activate.ps1
python src/main.py
```

Check that:
- The app starts without import errors
- Loading orders for a month works
- Product list search works
- Saving orders/expenses works
- No `backend.api` import errors

---

### Phase 2: Split qml_backend into multiple files

#### Step 9: Create `src/backend/qml_transformers.py`

**File:** `src/backend/qml_transformers.py` (new)

Extract all the ORM→dict and dict→ORM transformation logic from the current `qml_backend.py` methods into standalone functions. This file will contain:

- `orm_order_to_dict(order: Order) -> dict[str, Any]`
- `orm_product_to_dict(product: Product) -> dict[str, Any]`
- `dict_to_order_input(d: dict[str, Any]) -> OrderInput`
- `expense_to_dict(expense: Expense) -> dict[str, Any]`
- `product_page_to_dict(response: PageResponse[Product]) -> dict[str, Any]`
- `freight_result_to_dict(result: FreightDistributionResult) -> dict[str, Any]`
- `xml_import_result_to_dict(result: XmlImportResult) -> dict[str, Any]`

**Dependencies:** `Order`, `Product`, `Expense`, `OrderInput`, `ProductInput`, `PageResponse`, `FreightDistributionResult`, `XmlImportResult`

#### Step 10: Create `src/backend/qml_fetch.py`

**File:** `src/backend/qml_fetch.py` (new)

Create the `FetchHandler` class with:
- `__init__(session_factory, validation)` — but actually, validation isn't needed for fetch. Just `session_factory`.
- `_fetch_orders_for_month(month)` — the private method from qml_backend
- `_fetch_products(page, supplier, product, month)` — the private method from qml_backend
- `_fetch_expenses_for_month(month)` — the private method from qml_backend

**Dependencies:** `OrderRepository`, `ExpenseRepository`, `parse_month_for_orders`, `parse_month_for_expenses`, `Order`, `Product`, `Expense`, `PageResponse`, `Callable`, `Session`

#### Step 11: Create `src/backend/qml_save.py`

**File:** `src/backend/qml_save.py` (new)

Create the `SaveHandler` class with:
- `__init__(save_order_service, save_expense_service)`
- `_save_orders(orders, deleted_orders)`
- `_save_expenses(expenses, month)`

**Dependencies:** `SaveOrderService`, `SaveExpenseService`, `parse_month_for_expenses`, `ExpenseInput`, `OrderInput`

#### Step 12: Create `src/backend/qml_business.py`

**File:** `src/backend/qml_business.py` (new)

Create the `BusinessHandler` class with:
- `__init__(validation, freight, xml_import)`
- `distribute_freight(order_input)` — returns `FreightDistributionResult`
- `import_xml(file_path)` — returns `XmlImportResult`
- `validate_order(order_input)` — returns `ValidationResult`
- `validate_expense(description, value)` — returns `ValidationResult`

**Dependencies:** `ValidationService`, `FreightDistributionService`, `XmlImportService`, `OrderInput`

#### Step 13: Refactor `src/backend/qml_backend.py`

**File:** `src/backend/qml_backend.py`

Replace the entire content with the minimal composition-root version:

```python
from __future__ import annotations
import logging
from typing import Any, Callable
from PySide6.QtCore import QObject, Signal, Slot
from sqlalchemy.orm import Session
from backend.injector_module import get_injector
from backend.models.dto import ExpenseInput, OrderInput
from backend.services.freight_distribution import FreightDistributionService
from backend.services.save_order_service import SaveExpenseService, SaveOrderService
from backend.services.validation_service import ValidationService
from backend.qml_transformers import (
    orm_order_to_dict,
    orm_product_to_dict,
    dict_to_order_input,
    expense_to_dict,
    product_page_to_dict,
    freight_result_to_dict,
    xml_import_result_to_dict,
)
from backend.qml_fetch import FetchHandler
from backend.qml_save import SaveHandler
from backend.qml_business import BusinessHandler

logger = logging.getLogger(__name__)

class BackendManager(QObject):
    """QObject singleton that exposes backend API functions to QML."""
    data_changed = Signal()
    save_completed = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._injector = get_injector()
        self._session_factory: Callable[[], Session] = self._injector.get(Callable[[], Session])
        self._save_order_service = self._injector.get(SaveOrderService)
        self._save_expense_service = self._injector.get(SaveExpenseService)
        self._validation = ValidationService()
        self._freight = FreightDistributionService()
        self._xml_import = XmlImportService()
        # Sub-handlers
        self._fetch_handler = FetchHandler(self._session_factory)
        self._save_handler = SaveHandler(self._save_order_service, self._save_expense_service)
        self._business_handler = BusinessHandler(self._validation, self._freight, self._xml_import)

    # ── Data Fetch ──────────────────────────────────────────────────

    @Slot(str)
    def orders_for_month(self, month: str) -> list[dict[str, Any]]:
        try:
            raw_orders = self._fetch_handler.fetch_orders_for_month(month)
            self.data_changed.emit()
            return [orm_order_to_dict(o) for o in raw_orders]
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return []

    @Slot(int, str, str, str)
    def product_list(self, page: int, supplier: str = "", product: str = "", month: str = "") -> dict[str, Any]:
        try:
            result = self._fetch_handler.fetch_products(
                page=page,
                supplier=supplier if supplier else None,
                product=product if product else None,
                month=month if month else None,
            )
            return product_page_to_dict(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"items": [], "page": 0, "page_count": 0, "total": 0, "page_size": 0}

    @Slot(str)
    def expenses_for_month(self, month: str) -> list[dict[str, Any]]:
        try:
            raw_expenses = self._fetch_handler.fetch_expenses_for_month(month)
            return [expense_to_dict(e) for e in raw_expenses]
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return []

    # ── Save ────────────────────────────────────────────────────────

    @Slot(list, list)
    def save_orders(self, orders: list, deleted_orders: list) -> None:
        try:
            final_orders: list[OrderInput] = [dict_to_order_input(o) for o in orders]
            self._save_handler.save_orders(final_orders, deleted_orders)
            self.save_completed.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    @Slot(list, str)
    def save_expenses(self, expenses: list, month: str) -> None:
        try:
            expense_inputs = [ExpenseInput(description=e.get("description", ""), value=e.get("value", 0)) for e in expenses]
            self._save_handler.save_expenses(expense_inputs, month)
            self.save_completed.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Business Logic ──────────────────────────────────────────────

    @Slot(object)
    def distribute_freight(self, order: dict[str, Any]) -> dict[str, Any]:
        try:
            order_input = dict_to_order_input(order)
            result = self._business_handler.distribute_freight(order_input)
            return freight_result_to_dict(result)
        except ValueError as exc:
            self.error_occurred.emit(str(exc))
            return {}

    @Slot(str)
    def import_xml(self, file_path: str) -> dict[str, Any]:
        try:
            result = self._business_handler.import_xml(file_path)
            return xml_import_result_to_dict(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"orders": [], "warnings": []}

    @Slot(object)
    def validate_order(self, order: dict[str, Any]) -> dict[str, Any]:
        try:
            order_input = dict_to_order_input(order)
            result = self._business_handler.validate_order(order_input)
            return {"valid": result.valid, "errors": result.errors}
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"valid": False, "errors": [str(exc)]}

    @Slot(str, int)
    def validate_expense(self, description: str, value: int) -> dict[str, Any]:
        result = self._business_handler.validate_expense(description, value)
        return {"valid": result.valid, "errors": result.errors}
```

**Key changes from the monolithic version:**
- All `dict_to_order_input` repeated inline code is replaced with a single helper call
- All ORM→dict transformations are replaced with transformer function calls
- Each `@Slot` method is now 5-10 lines (delegation + try/except + signal)
- The class body is ~70 lines total

#### Step 14: Verify the app runs after split

```powershell
.\.venv\Scripts\Activate.ps1
python src/main.py
```

Check for:
- No import errors
- All `@Slot` methods callable from QML
- Correct return shapes (verify in QML console or by observing behavior)
- No circular import issues

---

## Implementation Order (Recommended)

To maintain a working state at each step, execute in this order:

1. **Step 1–4:** Merge api/ into qml_backend.py (update imports, __init__, add private methods, update Slot methods)
2. **Step 5:** Update `backend/__init__.py` (remove api re-exports)
3. **Step 6:** Update `qml_models.py` (replace api imports with direct repository access)
4. **Step 7:** Delete `api/` directory
5. **Step 8:** Verify app runs ✅ (end of Phase 1)
6. **Step 9:** Create `qml_transformers.py`
7. **Step 10:** Create `qml_fetch.py`
8. **Step 11:** Create `qml_save.py`
9. **Step 12:** Create `qml_business.py`
10. **Step 13:** Refactor `qml_backend.py` to use sub-handlers
11. **Step 14:** Verify app runs ✅ (end of Phase 2)

---

## Risks and Considerations

### Breaking changes
- **None to QML.** All `@Slot` signatures, signal names, and return types remain identical.
- **Breaking to external code** that imports from `backend.api.*`. Any code outside this repo that uses the api layer will break. Since this is a desktop app with no external API consumers, this is acceptable.

### `qml_models.py` concern
- `qml_models.py` currently uses the api layer's `call_with_injection` pattern. After the merge, it accesses the DI container directly via `get_injector()`. This works because the injector module maintains a module-level `_app_injector` singleton, so both `BackendManager` and `qml_models.py` share the same injector instance and thus the same engine/session factory. **This is safe.**

### Thread safety
- The injector creates a single shared `Engine`. Each `Session` is short-lived (session-per-operation pattern). The `StaticPool` with `check_same_thread=False` handles desktop-app threading. No changes needed.

### Type hints
- All new code must have full type hints per project rules. The proposed code above includes type annotations on all parameters and return types.

### `call_with_injection` module-level function
- After deleting `api/`, the `call_with_injection` function in `injector_module.py` is still used by `qml_models.py` indirectly (via `get_injector()`). The function itself can remain in `injector_module.py` as it may be useful for other purposes. It is **not deleted** — only the `api/` layer that used it is removed.

### Line count estimates (after Phase 2)

| File | Lines (est.) |
|---|---|
| `qml_backend.py` | ~70 |
| `qml_transformers.py` | ~80 |
| `qml_fetch.py` | ~40 |
| `qml_save.py` | ~25 |
| `qml_business.py` | ~30 |
| **Total new** | ~245 |
| **Old monolithic** | ~367 |
| **Reduction** | ~122 lines (33% smaller) |

### Known limitations / TODOs
- `qml_models.py` still accesses the injector directly. A future refactor could inject a session factory into the model classes via constructor, but that requires QML-side changes (passing the BackendManager or session factory to model constructors).
- The `call_with_injection` function in `injector_module.py` is now unused. Consider removing it in a future cleanup PR if no other code uses it.
- Error handling in `@Slot` methods is uniform (emit `error_occurred`, return empty/default). Consider centralizing this in a decorator or base handler method in a future refactor.
