# Implementation Plan: Refine IoC Container to Use `injector` Library

## Summary

This plan refines the existing IoC container plan to use the **`injector`** library instead of a custom `AppContainer` singleton. The `injector` library provides idiomatic, declarative dependency injection with `Module`, `Injector`, `@inject`, and `@provider` patterns. `BackendManager` becomes the composition root — the single place where the `Injector` is created and all services are wired. The public API surface and QML integration remain unchanged.

## Design Rationale

The previous plan created a custom `AppContainer` singleton with manual wiring (`set_container()` scattered across API modules). This is convoluted and error-prone. The `injector` library achieves the same decoupling with:

- **Declarative bindings** in a `Module` subclass — all wiring in one place
- **Constructor injection** via `@inject` — no manual `get_engine()` calls anywhere
- **Test isolation** via `Injector.clear_cache()` and per-test `Injector` instances
- **Idiomatic Python DI** — the most popular Python DI library, well-maintained

## Files to Create

### 1. `src/backend/injector_module.py` — Injector Configuration (NEW)

**Purpose:** Configures all dependency bindings in a single `Module` subclass. This is the composition root's configuration — the single source of truth for how dependencies are wired.

**Contents:**

```python
from __future__ import annotations

from typing import Callable

from injector import Injector, Module, provider, singleton
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.services.save_order_service import SaveExpenseService, SaveOrderService


class InjectorModule(Module):
    """
    Configures all dependency bindings for the Gessofer-Qt backend.

    - Engine: provided by the existing get_engine() function (backward compatible).
    - Session factory: a factory that creates new sessions on demand (session-per-operation).
    - SaveOrderService / SaveExpenseService: singletons that receive the Engine via @inject.
    """

    @provider
    @singleton
    def provide_engine(self) -> Engine:
        """Provide the shared database Engine via the existing get_engine() function."""
        return get_engine()

    @provider
    @singleton
    def provide_session_factory(self, engine: Engine) -> Callable[[], Session]:
        """
        Provide a session factory function.

        Each call to the returned function creates a new Session bound to the
        shared Engine. This implements the session-per-operation pattern.

        The factory captures the Engine reference resolved at configure time
        via constructor injection, avoiding circular references.

        Args:
            engine: The shared SQLAlchemy Engine (injected by the DI container).

        Returns:
            A callable that creates and returns a new SQLAlchemy Session.
        """

        def _session_factory() -> Session:
            return Session(engine)

        return _session_factory

    @singleton
    def provide_save_order_service(self, engine: Engine) -> SaveOrderService:
        """Provide a singleton SaveOrderService with the Engine injected."""
        return SaveOrderService(engine=engine)

    @singleton
    def provide_save_expense_service(self, engine: Engine) -> SaveExpenseService:
        """Provide a singleton SaveExpenseService with the Engine injected."""
        return SaveExpenseService(engine=engine)


def get_injector() -> Injector:
    """
    Create and return the application-wide Injector.

    This is the composition root — called once in BackendManager.__init__().

    Returns:
        The Injector instance configured with InjectorModule.
    """
    return Injector(InjectorModule)
```

**Key design decisions:**

- **`@provider` + `@singleton`**: The `@singleton` decorator ensures the Engine is created once and reused. The `@provider` decorator tells `injector` this is a factory method.
- **`provide_session_factory`**: Returns a *callable* (not a Session instance) so that each API call / service method gets a fresh Session. The closure captures the Engine reference resolved at configure time via constructor injection — no fragile frame-walking needed.
- **`provide_save_order_service` / `provide_save_expense_service`**: These are provider methods that receive `engine: Engine` as a parameter — `injector` automatically resolves and injects it. The `@singleton` decorator ensures only one instance is created.
- **`get_injector()`**: Simple factory function — the composition root. Called once in `BackendManager.__init__()`.

**Simplification vs. previous plan:** The `_get_engine_from_binder()` frame-walking hack has been removed. Instead, `provide_session_factory` receives `engine: Engine` as a constructor-injected parameter, which is the idiomatic `injector` pattern. This is simpler, more reliable, and easier to test.

---

## Files to Modify

### 2. `requirements.txt` — Add `injector` Dependency

**Current state:**
```
PySide6==6.11.1
PySide6_Addons==6.11.1
PySide6_Essentials==6.11.1
shiboken6==6.11.1
SQLAlchemy==2.0.51
```

**Changes needed:**
Add one line:

```
injector==0.22.0
```

**Rationale:** `injector` is a pure-Python, zero-dependency DI library. Version 0.22.0 is the latest stable as of 2024. Pin to a specific version for reproducible builds.

---

### 3. `src/backend/services/save_order_service.py` — Constructor Injection via `@inject`

**Current state:** `SaveOrderService` and `SaveExpenseService` have no explicit constructor (default `__init__`), and call `get_engine()` directly inside their `save_orders()` / `save_expenses()` methods (lines 70 and 144).

**Changes needed:**

```python
from __future__ import annotations

import logging
from typing import List

from injector import inject
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.errors import DatabaseError, ValidationError
from backend.models.dto import ExpenseInput, OrderInput
from backend.repositories.expense_repository import ExpenseRepository
from backend.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


class SaveOrderService:
    """
    Orchestrates the save-orders transaction.

    Algorithm (per Appendix B of business rules):
    1. Validate all input data.
    2. Begin a database transaction.
    3. Delete old orders (by ID) and their products.
    4. Insert new orders.
    5. Insert new products.
    6. Commit the transaction.

    If any step fails, rollback is automatic.
    """

    @inject
    def __init__(self, engine: Engine) -> None:
        """
        Initialize with an injected Engine.

        Args:
            engine: The shared SQLAlchemy Engine (injected by the DI container).
        """
        self._engine = engine

    def save_orders(
        self,
        orders: List[OrderInput],
        deleted_order_ids: List[str],
    ) -> None:
        """
        Save orders in a single transaction.

        Args:
            orders: List of OrderInput DTOs to insert.
            deleted_order_ids: List of order UUIDs to delete.

        Raises:
            ValidationError: If input data fails validation.
            DatabaseError: If a database error occurs.
        """
        # Step 1: Validate input
        validation_errors: list[str] = []
        for order in orders:
            if not order.id or not order.id.strip():
                validation_errors.append("ID de ordem vazio encontrado.")
            if not order.date or not order.date.strip():
                validation_errors.append(f"Data vazia na ordem {order.id}.")
            if not order.supplier or not order.supplier.strip():
                validation_errors.append(f"Fornecedor vazio na ordem {order.id}.")
            for product in order.products:
                if product.name and not product.quantity or product.quantity and not product.name:
                    validation_errors.append(
                        f"Nome e quantidade devem ser preenchidos juntos na ordem {order.id}."
                    )
                if product.price and (not product.quantity or not product.name):
                    validation_errors.append(
                        f"Preço requerido sem nome/quantidade na ordem {order.id}."
                    )

        if validation_errors:
            raise ValidationError(validation_errors, "Validação de pedidos falhou.")

        # Use injected engine to create session
        with Session(self._engine) as session:
            try:
                repo = OrderRepository(session)

                # Step 2: Delete old orders and their products
                if deleted_order_ids:
                    repo.delete_order_products(deleted_order_ids)
                    repo.delete_orders(deleted_order_ids)

                # Step 3: Insert new orders
                for order in orders:
                    repo.insert_order(order)

                # Step 4: Insert new products
                for order in orders:
                    for product in order.products:
                        repo.insert_product(product)

                # Session context manager commits on success, rolls back on exception
            except Exception as exc:
                logger.error("Erro ao salvar pedidos: %s", exc)
                raise DatabaseError(f"Falha na transação de salvamento de pedidos: {exc}") from exc


class SaveExpenseService:
    """
    Orchestrates the save-expenses transaction.

    Algorithm (per Appendix B of business rules):
    1. Validate all input data.
    2. Begin a database transaction.
    3. Delete existing expenses for the month.
    4. Insert new expenses.
    5. Commit the transaction.

    If any step fails, rollback is automatic.
    """

    @inject
    def __init__(self, engine: Engine) -> None:
        """
        Initialize with an injected Engine.

        Args:
            engine: The shared SQLAlchemy Engine (injected by the DI container).
        """
        self._engine = engine

    def save_expenses(
        self,
        expenses: List[ExpenseInput],
        month: str,
    ) -> None:
        """
        Save expenses in a single transaction.

        Args:
            expenses: List of ExpenseInput DTOs to insert.
            month: Month string in 'YYYY-MM' format.

        Raises:
            ValidationError: If input data fails validation.
            DatabaseError: If a database error occurs.
        """
        # Step 1: Validate input
        validation_errors: list[str] = []
        for expense in expenses:
            has_desc = bool(expense.description and expense.description.strip())
            has_value = expense.value is not None and expense.value != 0
            if has_desc != has_value:
                # One is filled but not the other — both or neither
                if has_desc:
                    validation_errors.append(
                        "Valor de despesa obrigatório quando descrição está preenchida."
                    )
                else:
                    validation_errors.append(
                        "Descrição de despesa obrigatória quando valor está preenchido."
                    )

        if validation_errors:
            raise ValidationError(validation_errors, "Validação de despesas falhou.")

        # Use injected engine to create session
        with Session(self._engine) as session:
            try:
                repo = ExpenseRepository(session)

                # Step 2: Delete existing expenses for the month
                repo.delete_expenses_for_month(month)

                # Step 3: Insert new expenses
                for expense in expenses:
                    repo.insert_expense(expense, month)

                # Session context manager commits on success, rolls back on exception
            except Exception as exc:
                logger.error("Erro ao salvar despesas: %s", exc)
                raise DatabaseError(f"Falha na transação de salvamento de despesas: {exc}") from exc
```

**Changes summary:**
- Added `from injector import inject` import
- Added `from sqlalchemy.engine import Engine` import
- Removed `from backend.database.connection import get_engine` import (no longer needed)
- Removed `from sqlalchemy.orm import Session` reordering (kept, just moved)
- Added `@inject` decorator to both `__init__` methods with `engine: Engine` parameter
- Replaced `engine = get_engine()` inside `save_orders()` with `Session(self._engine)`
- Replaced `engine = get_engine()` inside `save_expenses()` with `Session(self._engine)`

**Before (inside `save_orders` method):**
```python
engine = get_engine()
with Session(engine) as session:
    repo = OrderRepository(session)
```

**After:**
```python
with Session(self._engine) as session:
    repo = OrderRepository(session)
```

---

### 4. `src/backend/api/orders.py` — Session Factory Injection via `call_with_injection`

**Current state:** `orders_for_month()` and `product_list()` call `get_engine()` directly (lines 32 and 59).

**Changes needed:**

```python
from __future__ import annotations

from typing import Callable, List, Optional

from injector import call_with_injection
from sqlalchemy.orm import Session

from backend.entities.orm import Order, Product
from backend.models.dto import PageResponse
from backend.repositories.order_repository import OrderRepository
from backend.utils.date import parse_month_for_orders


def orders_for_month(
    month: str,
    session_factory: Callable[[], Session],
) -> List[Order]:
    """
    Fetch all orders and their products for a given month.

    Args:
        month: Month string in 'MM/yyyy' format (e.g., '07/2024').
        session_factory: Injected factory that creates new Sessions.

    Returns:
        List of Order ORM entities with products eagerly accessible.

    Raises:
        ValueError: If the month format is invalid.
        BackendError: If a database error occurs.
    """
    try:
        m, y = parse_month_for_orders(month)
    except ValueError as exc:
        raise ValueError(f"Formato de mês inválido: '{month}'. Esperado 'MM/yyyy'.") from exc

    with session_factory() as session:
        repo = OrderRepository(session)
        return repo.fetch_orders_for_month(month=m, year=y)


def product_list(
    page: int = 1,
    supplier: Optional[str] = None,
    product: Optional[str] = None,
    month: Optional[str] = None,
    session_factory: Callable[[], Session] = None,  # type: ignore[assignment]
) -> PageResponse[Product]:
    """
    Paginated product listing with optional filters.

    Args:
        page: Page number (1-based). Defaults to 1.
        supplier: Optional supplier name filter (fuzzy match).
        product: Optional product name filter (fuzzy match).
        month: Optional month filter in 'MM/yyyy' format.
        session_factory: Injected factory that creates new Sessions.

    Returns:
        PageResponse with matching Product ORM entities.

    Raises:
        BackendError: If a database error occurs.
    """
    with session_factory() as session:
        repo = OrderRepository(session)
        return repo.search_products(
            page=page,
            supplier=supplier,
            product=product,
            month=month,
        )


# Wrap functions with injection — BackendManager calls these wrapped versions
_orders_for_month_injected: Callable[[str], List[Order]] = call_with_injection(
    orders_for_month,
    caller=orders_for_month,
)

_product_list_injected: Callable[..., PageResponse[Product]] = call_with_injection(
    product_list,
    caller=product_list,
)


def get_orders_for_month_injected() -> Callable[[str], List[Order]]:
    """Return the injected version of orders_for_month for BackendManager."""
    return _orders_for_month_injected


def get_product_list_injected() -> Callable[..., PageResponse[Product]]:
    """Return the injected version of product_list for BackendManager."""
    return _product_list_injected
```

**Changes summary:**
- Added `from injector import call_with_injection` import
- Added `from typing import Callable` import
- Added `session_factory: Callable[[], Session]` parameter to both functions
- Removed `from backend.database.connection import get_engine` import
- Removed `engine = get_engine()` calls — replaced with `session_factory()`
- Created injected wrappers using `call_with_injection()`
- Added getter functions so `BackendManager` can access the injected versions

**Rationale for `call_with_injection`:** This decorator tells `injector` to resolve all annotated parameters (like `session_factory`) when the function is called. `BackendManager` calls the injected wrapper, not the original function. The wrapper handles dependency resolution transparently.

**Note on `caller` parameter:** The `caller` argument to `call_with_injection` tells `injector` which object to use for determining the injection context. Since these are module-level functions, we pass the function itself.

---

### 5. `src/backend/api/save_orders.py` — Service Injection via `call_with_injection`

**Current state:** Creates `SaveOrderService()` fresh each call (line 27). The service internally calls `get_engine()` (now fixed in service).

**Changes needed:**

```python
from __future__ import annotations

from typing import Callable, List

from injector import call_with_injection

from backend.models.dto import OrderInput
from backend.services.save_order_service import SaveOrderService


def save_orders(
    orders: List[OrderInput],
    deleted_orders: List[str],
    service: SaveOrderService,
) -> None:
    """
    Save orders in a single database transaction.

    This function is the API entry point for the 'save_orders' command.
    It delegates all business logic to SaveOrderService.

    Args:
        orders: List of OrderInput DTOs to save.
        deleted_orders: List of order UUIDs to delete.
        service: Injected SaveOrderService instance.

    Raises:
        ValidationError: If input data fails validation.
        DatabaseError: If a database or transaction error occurs.
    """
    service.save_orders(orders=orders, deleted_order_ids=deleted_orders)


# Wrap function with injection
_save_orders_injected: Callable[[List[OrderInput], List[str]], None] = call_with_injection(
    save_orders,
    caller=save_orders,
)


def get_save_orders_injected() -> Callable[[List[OrderInput], List[str]], None]:
    """Return the injected version of save_orders for BackendManager."""
    return _save_orders_injected
```

**Changes summary:**
- Added `from typing import Callable` import
- Added `from injector import call_with_injection` import
- Added `service: SaveOrderService` parameter
- Removed `service = SaveOrderService()` instantiation
- Replaced `service = SaveOrderService(); service.save_orders(...)` with `service.save_orders(...)`
- Created injected wrapper and getter function

**Note:** `SaveOrderService` is now a singleton bound in `InjectorModule`. The `call_with_injection()` decorator resolves it automatically.

---

### 6. `src/backend/api/save_expenses.py` — Service + Session Factory Injection

**Current state:** `expenses_for_month()` calls `get_engine()` (lines 31-32). `save_expenses()` creates `SaveExpenseService()` fresh each call (line 57).

**Changes needed:**

```python
from __future__ import annotations

from typing import Callable, List

from injector import call_with_injection
from sqlalchemy.orm import Session

from backend.entities.orm import Expense
from backend.models.dto import ExpenseInput
from backend.repositories.expense_repository import ExpenseRepository
from backend.services.save_order_service import SaveExpenseService
from backend.utils.date import parse_month_for_expenses


def expenses_for_month(
    month: str,
    session_factory: Callable[[], Session],
) -> List[Expense]:
    """
    Fetch all expenses for a given month.

    Args:
        month: Month string in 'YYYY-MM' format (e.g., '2024-07').
        session_factory: Injected factory that creates new Sessions.

    Returns:
        List of Expense ORM entities.

    Raises:
        ValueError: If the month format is invalid.
        BackendError: If a database error occurs.
    """
    validated_month = parse_month_for_expenses(month)

    with session_factory() as session:
        repo = ExpenseRepository(session)
        return repo.fetch_expenses_for_month(month=validated_month)


def save_expenses(
    expenses: List[ExpenseInput],
    month: str,
    service: SaveExpenseService,
) -> None:
    """
    Save expenses in a single database transaction.

    This function is the API entry point for the 'save_expenses' command.
    It delegates all business logic to SaveExpenseService.

    Args:
        expenses: List of ExpenseInput DTOs to save.
        month: Month string in 'YYYY-MM' format.
        service: Injected SaveExpenseService instance.

    Raises:
        ValidationError: If input data fails validation.
        DatabaseError: If a database or transaction error occurs.
    """
    validated_month = parse_month_for_expenses(month)
    service.save_expenses(expenses=expenses, month=validated_month)


# Wrap functions with injection
_expenses_for_month_injected: Callable[[str], List[Expense]] = call_with_injection(
    expenses_for_month,
    caller=expenses_for_month,
)

_save_expenses_injected: Callable[[List[ExpenseInput], str], None] = call_with_injection(
    save_expenses,
    caller=save_expenses,
)


def get_expenses_for_month_injected() -> Callable[[str], List[Expense]]:
    """Return the injected version of expenses_for_month for BackendManager."""
    return _expenses_for_month_injected


def get_save_expenses_injected() -> Callable[[List[ExpenseInput], str], None]:
    """Return the injected version of save_expenses for BackendManager."""
    return _save_expenses_injected
```

**Changes summary:**
- Added `from injector import call_with_injection` import
- Added `from typing import Callable` import
- Added `session_factory: Callable[[], Session]` parameter to `expenses_for_month()`
- Added `service: SaveExpenseService` parameter to `save_expenses()`
- Removed `from backend.database.connection import get_engine` import
- Removed `engine = get_engine()` call in `expenses_for_month()`
- Removed `service = SaveExpenseService()` instantiation in `save_expenses()`
- Created injected wrappers and getter functions

---

### 7. `src/backend/qml_backend.py` — Become the Composition Root

**Current state:** `BackendManager.__init__()` eagerly creates `ValidationService()`, `FreightDistributionService()`, `XmlImportService()`. No DI — all services are instantiated directly. API functions are called directly (e.g., `orders_for_month(month)`) rather than through injected wrappers.

**Changes needed:**

```python
from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, Slot
from sqlalchemy.orm import Session

from backend.injector_module import get_injector
from backend.models.dto import ExpenseInput, OrderInput
from backend.services.freight_distribution import FreightDistributionService
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportService

logger = logging.getLogger(__name__)


class BackendManager(QObject):
    """
    QObject singleton that exposes backend API functions to QML.

    All methods are @Slot-decorated so they can be called directly from QML.
    Errors are caught and emitted via the error_occurred signal.

    This class is the composition root for the PySide6 layer — it creates
    the Injector, resolves services, and wires them together.
    """

    data_changed = Signal()
    save_completed = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # Create the injector (composition root)
        self._injector = get_injector()

        # Resolve services from the injector
        self._session_factory: Callable[[], Session] = self._injector.get(Callable[[], Session])
        self._save_order_service = self._injector.get(SaveOrderService)
        self._save_expense_service = self._injector.get(SaveExpenseService)

        # Resolve injected API functions
        from backend.api.orders import (
            get_orders_for_month_injected,
            get_product_list_injected,
        )
        from backend.api.save_expenses import (
            get_expenses_for_month_injected,
            get_save_expenses_injected,
        )
        from backend.api.save_orders import get_save_orders_injected

        self._orders_for_month_fn = get_orders_for_month_injected()
        self._product_list_fn = get_product_list_injected()
        self._expenses_for_month_fn = get_expenses_for_month_injected()
        self._save_orders_fn = get_save_orders_injected()
        self._save_expenses_fn = get_save_expenses_injected()

        # Create stateless services (no DI needed)
        self._validation = ValidationService()
        self._freight = FreightDistributionService()
        self._xml_import = XmlImportService()

    # ── Orders ──────────────────────────────────────────────────────

    @Slot(str)
    def orders_for_month(self, month: str) -> list[dict[str, Any]]:
        """Fetch orders for a month and return as list of dicts for QML."""
        try:
            raw_orders = self._orders_for_month_fn(month)
            result = []
            for order in raw_orders:
                result.append({
                    "id": order.ID,
                    "date": order.DATE.isoformat() if order.DATE else "",
                    "supplier": order.SUPPLIER,
                    "nfeKey": order.NFE_KEY or "",
                    "freight": order.FREIGHT,
                    "unloading": order.UNLOADING,
                    "products": [
                        {
                            "id": p.ID,
                            "name": p.NAME,
                            "quantity": p.QUANTITY,
                            "price": p.PRICE,
                            "total": p.TOTAL_PRICE,
                            "order_id": p.ORDER_ID,
                            "itemOrdinal": p.ITEM_ORDINAL,
                        }
                        for p in order.products
                    ],
                })
            self.data_changed.emit()
            return result
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return []

    @Slot(int, str, str, str)
    def product_list(
        self,
        page: int,
        supplier: str = "",
        product: str = "",
        month: str = "",
    ) -> dict[str, Any]:
        """Fetch paginated product list and return as dict for QML."""
        try:
            result = self._product_list_fn(
                page=page,
                supplier=supplier if supplier else None,
                product=product if product else None,
                month=month if month else None,
            )
            return {
                "items": [
                    {
                        "id": p.ID,
                        "name": p.NAME,
                        "quantity": p.QUANTITY,
                        "price": p.PRICE,
                        "total": p.TOTAL_PRICE,
                        "order_id": p.ORDER_ID,
                        "itemOrdinal": p.ITEM_ORDINAL,
                    }
                    for p in result.items
                ],
                "page": result.page,
                "page_count": result.page_count,
                "total": result.total,
                "page_size": result.page_size,
            }
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {
                "items": [],
                "page": 0,
                "page_count": 0,
                "total": 0,
                "page_size": 0,
            }

    # ── Expenses ────────────────────────────────────────────────────

    @Slot(str)
    def expenses_for_month(self, month: str) -> list[dict[str, Any]]:
        """Fetch expenses for a month and return as list of dicts for QML."""
        try:
            raw_expenses = self._expenses_for_month_fn(month)
            return [
                {
                    "id": e.ID,
                    "month": e.MONTH,
                    "description": e.DESCRIPTION,
                    "value": e.VALUE,
                }
                for e in raw_expenses
            ]
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return []

    # ── Save Operations ─────────────────────────────────────────────

    @Slot(list, list)
    def save_orders(self, orders: list, deleted_orders: list) -> None:
        """Save orders in a single transaction."""
        try:
            # Build OrderInput list
            final_orders: list[OrderInput] = []
            for o in orders:
                products = []
                for p in o.get("products", []):
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
                oi = OrderInput(
                    id=o.get("id", ""),
                    date=o.get("date", ""),
                    supplier=o.get("supplier", ""),
                    nfe_key=o.get("nfeKey", ""),
                    freight=o.get("freight", 0),
                    unloading=o.get("unloading", 0),
                    products=products,
                )
                final_orders.append(oi)

            self._save_orders_fn(final_orders, deleted_orders)
            self.save_completed.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    @Slot(list, str)
    def save_expenses(self, expenses: list, month: str) -> None:
        """Save expenses in a single transaction."""
        try:
            expense_inputs = [
                ExpenseInput(
                    description=e.get("description", ""),
                    value=e.get("value", 0),
                )
                for e in expenses
            ]
            self._save_expenses_fn(expense_inputs, month)
            self.save_completed.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Business Logic ──────────────────────────────────────────────

    @Slot(object)
    def distribute_freight(self, order: dict[str, Any]) -> dict[str, Any]:
        """Distribute freight costs across products in an order."""
        try:
            order_input = OrderInput(
                id=order.get("id", ""),
                date=order.get("date", ""),
                supplier=order.get("supplier", ""),
                nfe_key=order.get("nfeKey", ""),
                freight=order.get("freight", 0),
                unloading=order.get("unloading", 0),
                products=[
                    OrderInput(
                        id=p.get("id", ""),
                        date="",
                        supplier="",
                        nfe_key="",
                        freight=0,
                        unloading=0,
                        products=[],
                    )
                    for p in order.get("products", [])
                ],
            )
            for i, p in enumerate(order.get("products", [])):
                order_input.products[i].name = p.get("name", "")
                order_input.products[i].quantity = p.get("quantity", 0)
                order_input.products[i].price = p.get("price", 0)
                order_input.products[i].total = p.get("total", 0)
                order_input.products[i].order_id = p.get("order_id", "")
                order_input.products[i].item_ordinal = p.get("itemOrdinal")

            result = self._freight.distribute(order_input)
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
        except ValueError as exc:
            self.error_occurred.emit(str(exc))
            return {}

    @Slot(str)
    def import_xml(self, file_path: str) -> dict[str, Any]:
        """Import data from an NFe XML file."""
        try:
            result = self._xml_import.parse_file(file_path)
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
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"orders": [], "warnings": []}

    @Slot(object)
    def validate_order(self, order: dict[str, Any]) -> dict[str, Any]:
        """Validate an order and return the result."""
        try:
            order_input = OrderInput(
                id=order.get("id", ""),
                date=order.get("date", ""),
                supplier=order.get("supplier", ""),
                nfe_key=order.get("nfeKey", ""),
                freight=order.get("freight", 0),
                unloading=order.get("unloading", 0),
                products=[
                    OrderInput(
                        id=p.get("id", ""),
                        date="",
                        supplier="",
                        nfe_key="",
                        freight=0,
                        unloading=0,
                        products=[],
                    )
                    for p in order.get("products", [])
                ],
            )
            for i, p in enumerate(order.get("products", [])):
                order_input.products[i].name = p.get("name", "")
                order_input.products[i].quantity = p.get("quantity", 0)
                order_input.products[i].price = p.get("price", 0)
                order_input.products[i].total = p.get("total", 0)
                order_input.products[i].order_id = p.get("order_id", "")
                order_input.products[i].item_ordinal = p.get("itemOrdinal")

            result = self._validation.validate_order(order_input)
            return {
                "valid": result.valid,
                "errors": result.errors,
            }
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"valid": False, "errors": [str(exc)]}

    @Slot(str, int)
    def validate_expense(self, description: str, value: int) -> dict[str, Any]:
        """Validate a single expense."""
        result = self._validation.validate_expense(description, value)
        return {
            "valid": result.valid,
            "errors": result.errors,
        }
```

**Changes summary:**
- Added `from injector import Injector` import (via `get_injector`)
- Added `from backend.injector_module import get_injector` import
- Added `from typing import Callable` import
- Added `from sqlalchemy.orm import Session` import
- Added `from backend.services.save_order_service import SaveOrderService, SaveExpenseService` import
- `__init__` now creates the `Injector` via `get_injector()`
- `__init__` resolves `SaveOrderService`, `SaveExpenseService`, and `Callable[[], Session]` from the injector
- `__init__` imports and stores injected API function wrappers
- All slot methods now call injected functions (`self._orders_for_month_fn`, etc.) instead of bare API functions
- Changed `except BackendError` to `except Exception` in slots — since injected functions may raise different exception types now, and `BackendError` is no longer imported

**Removed imports:**
- `from backend.api.orders import orders_for_month, product_list` → replaced with lazy imports of injected wrappers
- `from backend.api.save_expenses import expenses_for_month, save_expenses` → replaced with lazy imports
- `from backend.api.save_orders import save_orders` → replaced with lazy import
- `from backend.errors import BackendError` → no longer needed (changed to `except Exception`)
- `from backend.services.save_order_service import SaveOrderService, SaveExpenseService` → now imported for `self._injector.get()` resolution

---

### 8. `src/main.py` — No Changes Needed

**Current state:**
```python
from backend.qml_backend import BackendManager

backend = BackendManager()
engine.rootContext().setContextProperty("BackendManager", backend)
```

**Changes needed:** None. `BackendManager` creates the `Injector` internally in its `__init__()`. `main.py` remains clean and simple.

**Note:** The variable name `engine` is kept as-is (not renamed to `qml_engine`) since there's no ambiguity — the SQLAlchemy `Engine` is encapsulated inside the injector and never surfaces to this file.

---

### 9. `src/backend/__init__.py` — Update Re-exports

**Current state:**
```python
from .database.connection import get_engine, discover_database_path
from .entities.orm import Order, Product, Expense
from .models.dto import OrderInput, ProductInput, ExpenseInput, PageResponse
from .repositories.order_repository import OrderRepository
from .repositories.expense_repository import ExpenseRepository
from .utils.currency import cents_to_display, parse_currency_to_cents
from .utils.date import (
    parse_month_for_orders,
    parse_month_for_expenses,
    br_date_to_iso,
    iso_to_br_date,
    current_month_orders,
    current_month_expenses,
    format_time_now,
)
from .utils.text import normalize_text

# Errors
from .errors import BackendError, ValidationError, DatabaseError, XmlParseError

# Services
from .services.save_order_service import SaveOrderService, SaveExpenseService
from .services.freight_distribution import FreightDistributionService
from .services.xml_import_service import XmlImportService
from .services.validation_service import ValidationService

# API
from .api.orders import orders_for_month, product_list
from .api.save_orders import save_orders
from .api.save_expenses import expenses_for_month, save_expenses

__all__ = [ ... ]
```

**Changes needed:**

Add `InjectorModule` and `get_injector` to the re-exports:

```python
# Add near top, after the connection import:
from .injector_module import InjectorModule, get_injector

# Add to __all__:
    "InjectorModule",
    "get_injector",
```

**Full modified file:**
```python
from .database.connection import get_engine, discover_database_path
from .injector_module import InjectorModule, get_injector
from .entities.orm import Order, Product, Expense
from .models.dto import OrderInput, ProductInput, ExpenseInput, PageResponse
from .repositories.order_repository import OrderRepository
from .repositories.expense_repository import ExpenseRepository
from .utils.currency import cents_to_display, parse_currency_to_cents
from .utils.date import (
    parse_month_for_orders,
    parse_month_for_expenses,
    br_date_to_iso,
    iso_to_br_date,
    current_month_orders,
    current_month_expenses,
    format_time_now,
)
from .utils.text import normalize_text

# Errors
from .errors import BackendError, ValidationError, DatabaseError, XmlParseError

# Services
from .services.save_order_service import SaveOrderService, SaveExpenseService
from .services.freight_distribution import FreightDistributionService
from .services.xml_import_service import XmlImportService
from .services.validation_service import ValidationService

# API
from .api.orders import orders_for_month, product_list
from .api.save_orders import save_orders
from .api.save_expenses import expenses_for_month, save_expenses

__all__ = [
    # Database
    "get_engine",
    "discover_database_path",
    # Injector
    "InjectorModule",
    "get_injector",
    # Entities
    "Order",
    "Product",
    "Expense",
    # DTOs
    "OrderInput",
    "ProductInput",
    "ExpenseInput",
    "PageResponse",
    # Repositories
    "OrderRepository",
    "ExpenseRepository",
    # Utils
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
    # Errors
    "BackendError",
    "ValidationError",
    "DatabaseError",
    "XmlParseError",
    # Services
    "SaveOrderService",
    "SaveExpenseService",
    "FreightDistributionService",
    "XmlImportService",
    "ValidationService",
    # API
    "orders_for_month",
    "product_list",
    "save_orders",
    "expenses_for_month",
    "save_expenses",
]
```

**Rationale:** `InjectorModule` and `get_injector` are exported for testing purposes. Tests can import `get_injector()` to get the application injector and override bindings.

---

## Files to Delete

**None.** No files are deleted. `get_engine()` is kept in `connection.py` for backward compatibility and as the provider for the `Engine` binding.

---

## Data Model Changes

**None.** No database schema changes. The `Engine` still uses `StaticPool` with WAL mode and foreign keys enabled. The `Session` is still created per-operation using `with Session(engine) as session`.

---

## API Changes

**None to the public surface.** All public functions (`orders_for_month()`, `product_list()`, `save_orders()`, `expenses_for_month()`, `save_expenses()`) retain their exact signatures from the perspective of QML callers. The injected parameters (`session_factory`, `service`) are added to the function signatures, but `call_with_injection()` resolves them automatically — callers don't pass them.

---

## State Management Changes

**New state in `BackendManager`:**
- `_injector: Injector` — the application-wide injector instance
- `_session_factory: Callable[[], Session]` — resolved session factory
- `_save_order_service: SaveOrderService` — resolved singleton service
- `_save_expense_service: SaveExpenseService` — resolved singleton service
- `_orders_for_month_fn`, `_product_list_fn`, `_expenses_for_month_fn`, `_save_orders_fn`, `_save_expenses_fn` — injected API function wrappers

**New module-level state in API files:**
- `_orders_for_month_injected`, `_product_list_injected` in `orders.py`
- `_save_orders_injected` in `save_orders.py`
- `_expenses_for_month_injected`, `_save_expenses_injected` in `save_expenses.py`

---

## Testing Considerations

### How to Test with `injector`

The `injector` library provides excellent test isolation:

```python
# Example test: SaveOrderService with a test engine

import pytest
from injector import Injector, Module, provider
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.injector_module import InjectorModule, get_injector
from backend.services.save_order_service import SaveOrderService
from backend.models.dto import OrderInput


class TestInjectorModule(Module):
    """Override bindings for testing."""

    @provider
    def provide_test_engine(self):
        """Provide a test-specific Engine."""
        return create_engine("sqlite:///:memory:")


@pytest.fixture
def test_injector():
    """Create a fresh injector with test bindings."""
    inj = Injector([InjectorModule, TestInjectorModule])
    return inj


def test_save_orders_with_test_engine(test_injector: Injector) -> None:
    """Test SaveOrderService with an in-memory test database."""
    service = test_injector.get(SaveOrderService)

    orders = [
        OrderInput(
            id="test-1",
            date="2024-07-01",
            supplier="Test Supplier",
            products=[],
        )
    ]
    # This should work without any get_engine() calls
    service.save_orders(orders=orders, deleted_order_ids=[])
```

### Key Testing Patterns

1. **Per-test `Injector` instances:** Create a fresh `Injector([InjectorModule, TestModule])` for each test. This ensures complete isolation — no shared singleton state between tests.

2. **Test module overrides:** A `TestInjectorModule` that provides test doubles (in-memory DB, mock services) replaces production bindings when installed alongside `InjectorModule`.

3. **`Injector.clear_cache()`:** Clears cached singleton instances. Useful when reusing a single injector across multiple test scenarios.

4. **In-memory SQLite:** Use `create_engine("sqlite:///:memory:")` for fast, isolated tests.

### What Existing Tests Need Updating

- Any test that mocks `get_engine()` should instead use a `TestInjectorModule` with a test engine binding.
- Any test that instantiates `SaveOrderService()` directly needs to pass an `Engine` or use the injector.

### New Tests to Write

1. **`test_injector_module.py`**: Test that `InjectorModule` correctly binds all types.
2. **`test_save_order_service_injected.py`**: Test `SaveOrderService` with a mock engine.
3. **`test_save_expense_service_injected.py`**: Test `SaveExpenseService` with a mock engine.
4. **`test_api_orders_injected.py`**: Test API functions with injected session factory.
5. **`test_backend_manager.py`**: Test `BackendManager`'s injector setup.

---

## Risks and Considerations

### PySide6 `QObject` and `injector`

**Risk:** `BackendManager` is a `QObject` subclass. `injector` has no special handling for `QObject` — it just calls `__init__` with injected parameters.

**Mitigation:** We don't inject into `BackendManager.__init__()` directly. Instead, `BackendManager` creates its own `Injector` and resolves services manually via `self._injector.get()`. This avoids any `injector`-`QObject` interaction issues.

### Thread Safety

**Risk:** `injector` caches singletons in thread-local storage. In a multi-threaded app, different threads could get different singleton instances.

**Mitigation:** This is a single-user desktop app running on the main UI thread. All `injector` calls happen on the main thread. No threading concerns.

### `get_engine()` Still Called

**Risk:** `get_engine()` is still called inside `InjectorModule.provide_engine()`. This doesn't eliminate the call — it just moves it to the composition root.

**Mitigation:** The composition root is the *one* place that's allowed to call `get_engine()`. All other code receives the `Engine` via injection. This achieves the goal: services and API functions no longer call `get_engine()` directly.

### `call_with_injection()` for Plain Functions

**Risk:** Using `call_with_injection()` on plain functions is less common than constructor injection. Tests need to call the injected wrapper, not the original function.

**Mitigation:** The getter functions (`get_orders_for_month_injected()`, etc.) make this explicit. Tests can import and use these getters. The original functions are still accessible for non-DI testing if needed.

### `Injector` Creation in `BackendManager.__init__`

**Risk:** The `Injector` is created every time `BackendManager()` is instantiated. If `BackendManager` is recreated (e.g., during testing), a new injector is created.

**Mitigation:** This is the desired behavior for testing. In production, `BackendManager` is created once in `main.py`. For tests, create a fresh `BackendManager` to get a fresh `Injector`.

### SQLAlchemy Session and `injector` Provider

**Risk:** The session factory closure captures the `Engine` reference. If the engine is ever replaced (e.g., during testing), the closure still points to the old engine.

**Mitigation:** Each test creates a fresh `Injector` instance (see testing patterns above), so the session factory is always bound to the test engine. No stale closure risk.

### Backward Compatibility of `get_engine()`

**Risk:** If external code (tests, scripts) depends on `get_engine()`, removing it would break them.

**Mitigation:** `get_engine()` is kept in `connection.py` and re-exported in `__init__.py`. It remains fully functional for backward compatibility.

---

## Implementation Order

The following sequence minimizes breakage and keeps the app runnable after each step:

### Step 1: Add `injector` to `requirements.txt`

- Add `injector==0.22.0` to `requirements.txt`
- Run `pip install -r requirements.txt`
- **Verify:** `python -c "import injector; print('OK')"` passes

### Step 2: Create `src/backend/injector_module.py`

- Create the file with `InjectorModule` and `get_injector()`
- **Verify:** `python -c "from backend.injector_module import InjectorModule, get_injector; print('OK')"` passes

### Step 3: Refactor `services/save_order_service.py`

- Add `@inject` to `__init__` with `engine: Engine` parameter
- Replace `get_engine()` calls with `Session(self._engine)`
- **Verify:** `python -c "from backend.services.save_order_service import SaveOrderService; print('OK')"` passes (may fail if no DB, but imports work)
- **Verify:** No `get_engine()` calls remain in this file

### Step 4: Refactor `api/orders.py`

- Add `session_factory` parameter to both functions
- Remove `get_engine()` calls
- Add `call_with_injection()` wrappers and getters
- **Verify:** No `get_engine()` calls remain in this file

### Step 5: Refactor `api/save_orders.py`

- Add `service` parameter
- Remove `SaveOrderService()` instantiation
- Add `call_with_injection()` wrapper and getter
- **Verify:** No `SaveOrderService()` direct instantiation remains

### Step 6: Refactor `api/save_expenses.py`

- Add `session_factory` parameter to `expenses_for_month()`
- Add `service` parameter to `save_expenses()`
- Remove `get_engine()` and `SaveExpenseService()` calls
- Add `call_with_injection()` wrappers and getters
- **Verify:** No `get_engine()` calls remain in this file

### Step 7: Refactor `qml_backend.py`

- Create `Injector` in `__init__`
- Resolve services and injected API functions
- Update all slot methods to use injected functions
- **Verify:** `python src/main.py` launches the app

### Step 8: Update `src/backend/__init__.py`

- Add `InjectorModule` and `get_injector` to imports and `__all__`
- **Verify:** `python -c "from backend import InjectorModule, get_injector; print('OK')"` passes

### Step 9: Verification and Cleanup

- Run `rg "get_engine\(\)" src/backend/api/ src/backend/services/` — expect **zero matches**
- Run the full app and test all operations manually
- Write unit tests for the injected services

---

## Verification Steps

### Automated Checks

1. **No remaining `get_engine()` calls in services or API functions:**
   ```powershell
   rg "get_engine\(\)" src/backend/api/ src/backend/services/
   ```
   Expected result: **zero matches**. (Calls in `connection.py` and `injector_module.py` are fine.)

2. **Import verification:**
   ```powershell
   python -c "from backend.injector_module import InjectorModule, get_injector; print('Injector module OK')"
   ```

3. **Injector creation verification:**
   ```powershell
   python -c "
   from backend.injector_module import get_injector
   inj = get_injector()
   print('Injector created OK')
   "
   ```
   (This may fail if no DB exists, which is expected.)

4. **App startup test:**
   ```powershell
   python src/main.py
   ```
   Expected: App launches without errors.

### Manual Verification

5. **Load orders for a month:**
   - Open the app, select a month
   - Verify orders display correctly
   - This exercises: `BackendManager.orders_for_month()` → injected `orders_for_month()` → `session_factory()` → `OrderRepository`

6. **Load products list:**
   - Navigate to products view
   - Verify paginated list loads
   - This exercises: `BackendManager.product_list()` → injected `product_list()` → `session_factory()` → `OrderRepository.search_products()`

7. **Load expenses for a month:**
   - Navigate to expenses view
   - Verify expenses display
   - This exercises: `BackendManager.expenses_for_month()` → injected `expenses_for_month()` → `session_factory()` → `ExpenseRepository`

8. **Save orders:**
   - Modify an order and save
   - Verify save completes without error
   - This exercises: `BackendManager.save_orders()` → injected `save_orders()` → injected `SaveOrderService` → `Session(self._engine)` → `OrderRepository`

9. **Save expenses:**
   - Modify an expense and save
   - Verify save completes without error
   - This exercises: `BackendManager.save_expenses()` → injected `save_expenses()` → injected `SaveExpenseService` → `Session(self._engine)` → `ExpenseRepository`

10. **Error handling:**
    - Trigger a validation error (empty order)
    - Verify error signal is emitted and displayed

11. **XML import:**
    - Import an NFe XML file
    - Verify parsed data displays (unchanged — no DB dependency)

12. **Freight distribution:**
    - Distribute freight on an order
    - Verify prices update correctly (unchanged — pure computation)

---

## Summary of `get_engine()` Call Sites (5 → 0 in services/API)

| # | File | Line | Before | After |
|---|------|------|--------|-------|
| 1 | `api/orders.py` | 32 | `engine = get_engine()` | `session_factory()` (injected) |
| 2 | `api/orders.py` | 59 | `engine = get_engine()` | `session_factory()` (injected) |
| 3 | `api/save_expenses.py` | 31 | `engine = get_engine()` | `session_factory()` (injected) |
| 4 | `services/save_order_service.py` | 70 | `engine = get_engine()` | `Session(self._engine)` (injected) |
| 5 | `services/save_order_service.py` | 144 | `engine = get_engine()` | `Session(self._engine)` (injected) |

After this refactoring, `get_engine()` is called **zero times** in services or API functions. It remains only in:
- `connection.py` — the original function (kept for backward compatibility)
- `injector_module.py` — the single composition root binding

---

## Appendix: Before/After Comparison

### Before: `services/save_order_service.py`
```python
from backend.database.connection import get_engine

class SaveOrderService:
    def save_orders(self, orders, deleted_order_ids):
        engine = get_engine()  # ← Direct dependency
        with Session(engine) as session:
            repo = OrderRepository(session)
```

### After: `services/save_order_service.py`
```python
from injector import inject
from sqlalchemy.engine import Engine

class SaveOrderService:
    @inject
    def __init__(self, engine: Engine) -> None:  # ← Injected
        self._engine = engine

    def save_orders(self, orders, deleted_order_ids):
        with Session(self._engine) as session:  # ← Injected dependency
            repo = OrderRepository(session)
```

### Before: `api/orders.py`
```python
from backend.database.connection import get_engine

def orders_for_month(month: str) -> List[Order]:
    engine = get_engine()  # ← Direct dependency
    with Session(engine) as session:
        repo = OrderRepository(session)
```

### After: `api/orders.py`
```python
from injector import call_with_injection
from typing import Callable
from sqlalchemy.orm import Session

def orders_for_month(
    month: str,
    session_factory: Callable[[], Session],  # ← Injected
) -> List[Order]:
    with session_factory() as session:  # ← Injected dependency
        repo = OrderRepository(session)

# Injected wrapper for BackendManager
_orders_for_month_injected = call_with_injection(orders_for_month, caller=orders_for_month)
```

### Before: `qml_backend.py` (constructor)
```python
def __init__(self, parent: QObject | None = None) -> None:
    super().__init__(parent)
    self._validation = ValidationService()
    self._freight = FreightDistributionService()
    self._xml_import = XmlImportService()
```

### After: `qml_backend.py` (constructor)
```python
def __init__(self, parent: QObject | None = None) -> None:
    super().__init__(parent)
    self._injector = get_injector()  # ← Composition root
    self._session_factory = self._injector.get(Callable[[], Session])
    self._save_order_service = self._injector.get(SaveOrderService)
    self._save_expense_service = self._injector.get(SaveExpenseService)
    # ... resolve injected API functions ...
    self._validation = ValidationService()
    self._freight = FreightDistributionService()
    self._xml_import = XmlImportService()
```

---

## Appendix: `injector` Library Usage Reference

### Key Classes and Decorators Used

| Symbol | Purpose | Usage in this plan |
|--------|---------|-------------------|
| `Module` | Configure bindings declaratively | `InjectorModule` |
| `Injector` | DI container | Created by `get_injector()` |
| `@inject` | Mark constructor for injection | `SaveOrderService.__init__`, `SaveExpenseService.__init__` |
| `@provider` | Custom factory method | `provide_engine`, `provide_session_factory`, `provide_save_order_service`, `provide_save_expense_service` |
| `@singleton` | Ensure single instance | All providers that return shared objects |
| `call_with_injection()` | Inject into plain functions | API functions (`orders_for_month`, `product_list`, etc.) |
| `Injector.get(Type)` | Resolve a bound instance | `BackendManager` resolves services |
| `Injector.clear_cache()` | Clear singleton cache | Testing — reset singletons between tests |

### How `call_with_injection()` Works

```python
# Original function
def orders_for_month(month: str, session_factory: Callable[[], Session]) -> List[Order]:
    with session_factory() as session:
        ...

# Create injected wrapper
_injected = call_with_injection(orders_for_month, caller=orders_for_month)

# Call the wrapper — injector resolves session_factory automatically
injected("07/2024")  # session_factory is injected automatically
```

The `caller` argument tells `injector` which object's context to use for resolving dependencies. For module-level functions, pass the function itself.

### Testing with `injector`

```python
# Create a fresh injector with test bindings (per-test isolation)
inj = Injector([InjectorModule, TestInjectorModule])

# Get a service with test engine
service = inj.get(SaveOrderService)

# Clear cached singletons (when reusing an injector)
inj.clear_cache()
```
