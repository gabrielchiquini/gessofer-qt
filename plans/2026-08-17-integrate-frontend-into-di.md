# Implementation Plan: DI Integration — Bridge Classes & Dialog Factories

## Summary

This plan migrates the frontend layer from a **function-call bridge pattern** (where widgets call bridge functions that internally resolve services via lazy `get_injector().get(...)`) to a **constructor-injection pattern** (where frontend classes receive their dependencies — bridge classes, dialog factories, and view factories — through their constructors, wired by the DI container). Each bridge module is transformed into a class registered as a DI singleton. Dialogs are constructed exclusively through factory functions registered in DI. Views are constructed on-demand via **view factory functions** registered in DI.

## Architecture Decision

**Where to register frontend classes:** Extend `InjectorModule` in `src/backend/injector_module.py` rather than creating a separate frontend DI module. This avoids circular imports (frontend imports bridge, bridge imports backend services, and a separate frontend DI module would need to import both). The injector is already the composition root; it simply needs more bindings.

**Scope strategy:**
- **Singletons:** Backend services, handlers, bridge classes, dialog factories, view factories.
- **Non-singleton (provision):** All frontend view classes and dialog classes — constructed fresh each time a factory is called.

---

## Phase 1: Register Backend Handlers as Singletons

The following backend handlers already exist but are **not registered** in `InjectorModule`. They must be registered so the DI container can provide them to bridge classes.

### File: `src/backend/injector_module.py`

**Current state:** Registers `SaveOrderService`, `SaveExpenseService`, `NfeSearchService`, `BackupService`, `Engine`, `SessionFactory`. Does **not** register `FetchHandler`, `SaveHandler`, `ExpenseFetchHandler`, `ExpenseSaveHandler`, or `_CertificateHandler`.

**Changes needed:**

1. Add imports at the top of the file:
    ```python
    from backend.services.fetch_handler import FetchHandler
    from backend.services.save_handler import SaveHandler
    from backend.services.expense_fetch_handler import ExpenseFetchHandler
    from backend.services.expense_save_handler import ExpenseSaveHandler
    from bridge.certificate import _CertificateHandler
    ```

2. Add five new `@singleton` provider methods in `InjectorModule`:
    ```python
    @singleton
    def provide_fetch_handler(self, session_factory: Callable[[], Session]) -> FetchHandler:
        return FetchHandler(session_factory=session_factory)

    @singleton
    def provide_save_handler(
        self,
        save_order_service: SaveOrderService,
        save_expense_service: SaveExpenseService,
    ) -> SaveHandler:
        return SaveHandler(
            save_order_service=save_order_service,
            save_expense_service=save_expense_service,
        )

    @singleton
    def provide_expense_fetch_handler(
        self, session_factory: Callable[[], Session],
    ) -> ExpenseFetchHandler:
        return ExpenseFetchHandler(session_factory=session_factory)

    @singleton
    def provide_expense_save_handler(
        self, save_expense_service: SaveExpenseService,
    ) -> ExpenseSaveHandler:
        return ExpenseSaveHandler(save_expense_service=save_expense_service)

    @singleton
    def provide_certificate_handler(self) -> _CertificateHandler:
        return _CertificateHandler()
    ```

**Rationale:** These handlers are stateless wrappers around services/repos. They are safe singletons because each method creates its own `Session` via the injected `session_factory`.

---

## Phase 2: Register Business Services as Singletons

### File: `src/backend/injector_module.py`

**Changes needed:** Register three additional services as singletons.

1. Add imports:
    ```python
    from backend.services.freight_distribution import FreightDistributionService
    from backend.services.xml_import_service import XmlImportService
    from backend.services.validation_service import ValidationService
    ```

2. Add provider methods:
    ```python
    @singleton
    def provide_freight_distribution_service(self) -> FreightDistributionService:
        return FreightDistributionService()

    @singleton
    def provide_xml_import_service(self) -> XmlImportService:
        return XmlImportService()

    @singleton
    def provide_validation_service(self) -> ValidationService:
        return ValidationService()
    ```

---

## Phase 3: Transform Bridge Modules into DI-Mapped Classes

Each bridge module is transformed into a **class** that receives its dependencies via constructor injection and exposes **methods** instead of module-level functions. The bridge classes are registered as singletons in `InjectorModule`.

### 3.1: `ProductBridge` — `src/bridge/product.py`

**Current state:** Module-level functions `fetch_products()` and `fetch_orders_for_month()` that call `get_injector().get(FetchHandler)` internally. Helper functions `orm_product_to_dict`, `orm_order_to_dict`, `product_list_item_to_dict` are module-level.

**Changes needed:**

1. Wrap the module in a `ProductBridge` class:
    ```python
    class ProductBridge:
        """Bridge for product-related fetch operations."""

        def __init__(self, fetch_handler: FetchHandler) -> None:
            self._fetch_handler = fetch_handler

        def fetch_products(
            self,
            page: int,
            supplier: str = "",
            product: str = "",
            month: str = "",
        ) -> BridgePageResponse[ProductListItem]:
            """Fetch paginated product list with optional filters."""
            try:
                return self._fetch_handler.fetch_products(
                    page,
                    supplier or None,
                    product or None,
                    month or None,
                )
            except Exception as exc:
                logger.error("Error in fetch_products: %s", exc)
                logger.debug("Traceback", exc_info=True)
                return BridgePageResponse(
                    items=[], page=page, page_count=0, total=0, page_size=50,
                )

        def fetch_orders_for_month(self, month: str) -> list[OrderDataclass]:
            """Fetch all orders for a given month."""
            try:
                return self._fetch_handler.fetch_orders_for_month(month)
            except Exception as exc:
                logger.error("Error in fetch_orders_for_month: %s", exc)
                logger.debug("Traceback", exc_info=True)
                return []

        # Helper functions become methods:
        def orm_product_to_dict(self, product: Product) -> ProductDataclass:
            return ProductDataclass(
                id=product.ID,
                name=product.NAME,
                quantity=product.QUANTITY,
                price=product.PRICE,
                total=product.TOTAL_PRICE,
                order_id=product.ORDER_ID,
                item_ordinal=product.ITEM_ORDINAL,
            )

        def orm_order_to_dict(self, order: Order) -> OrderDataclass:
            return OrderDataclass(
                id=order.ID,
                date=order.DATE.isoformat() if order.DATE else "",
                supplier=order.SUPPLIER,
                nfe_key=order.NFE_KEY or "",
                freight=order.FREIGHT,
                unloading=order.UNLOADING,
                products=[self.orm_product_to_dict(p) for p in order.products],
            )

        def product_list_item_to_dict(self, product: Product) -> ProductListItem:
            date_str = datetime_to_br_date(product.order.DATE)
            return ProductListItem(
                date=date_str,
                supplier=product.order.SUPPLIER if product.order else "",
                name=product.NAME,
                price=cents_to_display(product.PRICE),
                total_price=cents_to_display(product.TOTAL_PRICE),
                order_id=product.ORDER_ID,
            )
    ```

2. Keep the module-level `__all__` exports for backward compatibility **only if needed** — but since frontend widgets will use the bridge class directly, the old function exports can be removed. Update `bridge/__init__.py` accordingly.

### 3.2: `OrderBridge` — `src/bridge/order.py`

**Current state:** `save_single_order()` calls `get_injector().get(SaveHandler)`. `fetch_order_by_id()` calls `get_injector().get(Callable[[], Session])` directly.

**Changes needed:**

```python
class OrderBridge:
    """Bridge for order-related save and fetch operations."""

    def __init__(
        self,
        save_handler: SaveHandler,
        session_factory: Callable[[], Session],
    ) -> None:
        self._save_handler = save_handler
        self._session_factory = session_factory

    def save_single_order(self, order: OrderInput) -> bool:
        """Save a single order (with its products) as an upsert."""
        try:
            self._save_handler.save_single_order(order)
            return True
        except Exception as exc:
            logger.error("Error in save_single_order: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return False

    def fetch_order_by_id(self, order_id: str) -> Order | None:
        """Fetch a single order by UUID, including all products."""
        session: Session = self._session_factory()
        try:
            repo = OrderRepository(session)
            order = repo.fetch_order_by_id(order_id)
            if order is None:
                return None
            return self.orm_order_to_dict(order)
        finally:
            session.close()

    def orm_order_to_dict(self, order: Order) -> Order:
        """Transform an ORM Order entity into an Order dataclass."""
        return Order(
            id=order.ID,
            date=order.DATE.isoformat() if order.DATE else "",
            supplier=order.SUPPLIER,
            nfe_key=order.NFE_KEY or "",
            freight=order.FREIGHT,
            unloading=order.UNLOADING,
            products=[self.orm_product_to_dict(p) for p in order.products],
        )

    def orm_product_to_dict(self, product: Product) -> ProductDataclass:
        return ProductDataclass(
            id=product.ID,
            name=product.NAME,
            quantity=product.QUANTITY,
            price=product.PRICE,
            total=product.TOTAL_PRICE,
            order_id=product.ORDER_ID,
            item_ordinal=product.ITEM_ORDINAL,
        )
    ```

**Note:** `OrderBridge` imports `orm_product_to_dict` logic from `bridge.product`. To avoid circular imports between `ProductBridge` and `OrderBridge`, `OrderBridge` should either:
- Import `ProductBridge` lazily inside `orm_product_to_dict`, or
- Import the helper functions directly from `bridge.product` (the module-level helper functions still exist as standalone functions — see "Backward Compatibility" below), or
- Have `ProductBridge` expose its helpers as methods and `OrderBridge` call `product_bridge.orm_product_to_dict()` (requires `ProductBridge` injection into `OrderBridge`).

**Recommended approach:** Keep the helper functions as **standalone module-level functions** in `bridge/product.py` (not methods) for use by `OrderBridge` and `OrderSummaryBridge`. The class methods are the primary API. The standalone functions are kept for cross-bridge reuse and backward compatibility.

### 3.3: `ExpenseBridge` — `src/bridge/expense.py`

**Current state:** `fetch_expenses_for_month()` calls `get_injector().get(ExpenseFetchHandler)`. `save_expenses()` calls `get_injector().get(ExpenseSaveHandler)`.

**Changes needed:**

```python
class ExpenseBridge:
    """Bridge for expense-related fetch and save operations."""

    def __init__(
        self,
        expense_fetch_handler: ExpenseFetchHandler,
        expense_save_handler: ExpenseSaveHandler,
    ) -> None:
        self._expense_fetch_handler = expense_fetch_handler
        self._expense_save_handler = expense_save_handler

    def fetch_expenses_for_month(self, month: str) -> ExpensesForMonthOutput:
        """Fetch expenses for a given month."""
        try:
            m_str, y_str = month.strip().split("/")
            yyyy_mm = f"{y_str}-{m_str}"
            return self._expense_fetch_handler.fetch_expenses_for_month(yyyy_mm)
        except Exception as exc:
            logger.error("Error in fetch_expenses_for_month: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return ExpensesForMonthOutput(expenses=[], total=0)

    def save_expenses(
        self,
        expenses: list[ExpenseInput],
        month: str,
    ) -> bool:
        """Save a list of expenses for a given month."""
        try:
            m_str, y_str = month.strip().split("/")
            yyyy_mm = f"{y_str}-{m_str}"
            expense_inputs: list[ExpenseInput] = [
                ExpenseInput(description=e.description, value=e.value)
                for e in expenses
            ]
            self._expense_save_handler.save_expenses(expense_inputs, yyyy_mm)
            return True
        except Exception as exc:
            logger.error("Error in save_expenses: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return False
```

### 3.4: `NfeBridge` — `src/bridge/nfe.py`

**Current state:** Uses `_nfe_handler` module-level variable and `_get_nfe_handler()` lazy singleton. `search_nfe_key()` delegates to the handler.

**Changes needed:**

```python
class NfeBridge:
    """Bridge for NFe search operations."""

    def __init__(self, nfe_search_service: NfeSearchService) -> None:
        self._nfe_search_service = nfe_search_service

    def search_nfe_key(self, nfe_key: str) -> str:
        """Search for an NFe via SEFAZ, save XML, return file path."""
        return self._nfe_search_service.search_and_save(nfe_key)
```

Remove `_nfe_handler` module-level variable and `_get_nfe_handler()` function entirely.

### 3.5: `CertificateBridge` — `src/bridge/certificate.py`

**Current state:** Uses `_handler` module-level variable and `_get_handler()` lazy singleton. `_CertificateHandler` is not DI-registered.

**Changes needed:**

```python
class CertificateBridge:
    """Bridge for certificate operations."""

    def __init__(self, certificate_handler: _CertificateHandler) -> None:
        self._certificate_handler = certificate_handler

    def fetch_certificate_info(self) -> CertificateInfo:
        """Fetch certificate information from the stored PEM file."""
        try:
            return self._certificate_handler.fetch_certificate_info()
        except Exception as exc:
            logger.error("Error fetching certificate info: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return CertificateInfo(
                owner="Nenhum certificado registrado",
                expiration_date="",
                is_valid=False,
            )

    def save_certificate_from_pfx(
        self, pfx_path: str, pfx_password: str
    ) -> bool:
        """Import a PFX certificate file and save PEM + private key."""
        return self._certificate_handler.save_certificate_from_pfx(
            pfx_path, pfx_password
        )
```

Remove `_handler` module-level variable and `_get_handler()` function.

### 3.6: `OrderSummaryBridge` — `src/bridge/order_summary.py`

**Current state:** `fetch_order_summaries()` calls `bridge.product.fetch_orders_for_month(month)` internally.

**Changes needed:**

```python
class OrderSummaryBridge:
    """Bridge for order summary operations."""

    def __init__(self, product_bridge: ProductBridge) -> None:
        self._product_bridge = product_bridge

    def fetch_order_summaries(self, month: str) -> list[OrderSummary]:
        """Fetch order summaries for a given month."""
        try:
            orders: list[Order] = self._product_bridge.fetch_orders_for_month(month)
            summaries: list[OrderSummary] = []
            for order in orders:
                products_total: int = sum(p.total for p in order.products)
                order_total: int = products_total + order.freight + order.unloading
                summaries.append(
                    OrderSummary(
                        id=order.id,
                        date=order.date,
                        supplier=order.supplier,
                        product_count=len(order.products),
                        products_total=products_total,
                        order_total=order_total,
                    )
                )
            return summaries
        except Exception as exc:
            logger.error("Error in fetch_order_summaries: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return []
```

### 3.7: `InjectorModule` — Register Bridge Classes as Singletons

Add these provider methods to `InjectorModule`:

```python
@singleton
def provide_product_bridge(self, fetch_handler: FetchHandler) -> ProductBridge:
    return ProductBridge(fetch_handler=fetch_handler)

@singleton
def provide_order_bridge(
    self,
    save_handler: SaveHandler,
    session_factory: Callable[[], Session],
) -> OrderBridge:
    return OrderBridge(save_handler=save_handler, session_factory=session_factory)

@singleton
def provide_expense_bridge(
    self,
    expense_fetch_handler: ExpenseFetchHandler,
    expense_save_handler: ExpenseSaveHandler,
) -> ExpenseBridge:
    return ExpenseBridge(
        expense_fetch_handler=expense_fetch_handler,
        expense_save_handler=expense_save_handler,
    )

@singleton
def provide_nfe_bridge(self, nfe_search_service: NfeSearchService) -> NfeBridge:
    return NfeBridge(nfe_search_service=nfe_search_service)

@singleton
def provide_certificate_bridge(
    self, certificate_handler: _CertificateHandler
) -> CertificateBridge:
    return CertificateBridge(certificate_handler=certificate_handler)

@singleton
def provide_order_summary_bridge(
    self, product_bridge: ProductBridge
) -> OrderSummaryBridge:
    return OrderSummaryBridge(product_bridge=product_bridge)
```

### 3.8: `bridge/__init__.py` — Update Exports

Update `TYPE_CHECKING` imports to reference the new class methods instead of module-level functions. The `__all__` list should be updated to reflect the new public API:

```python
if TYPE_CHECKING:
    from bridge.product import ProductBridge
    from bridge.order import OrderBridge
    from bridge.expense import ExpenseBridge
    from bridge.nfe import NfeBridge
    from bridge.certificate import CertificateBridge
    from bridge.order_summary import OrderSummaryBridge
```

Remove the old function imports from `__all__` (or keep them as re-exports from bridge instances if backward compatibility is needed).

---

## Phase 4: Transform `business.py` into `BusinessService` Class

### File: `src/frontend/business.py`

**Current state:** Functions like `distribute_freight()`, `import_xml()`, `validate_order()`, `validate_expense()` instantiate services directly:
```python
service = FreightDistributionService()
service = XmlImportService()
service = ValidationService()
```

**Changes needed:**

1. Transform the module into a `BusinessService` class that receives its services via constructor injection:
    ```python
    class BusinessService:
        def __init__(
            self,
            freight_service: FreightDistributionService,
            xml_service: XmlImportService,
            validation_service: ValidationService,
        ) -> None:
            self._freight_service = freight_service
            self._xml_service = xml_service
            self._validation_service = validation_service

        def distribute_freight(self, order: OrderInput) -> FreightResult:
            ...

        def import_xml(self, file_path: str) -> XmlImportResult:
            ...

        def validate_order(self, order: OrderInput) -> Validation:
            ...

        def validate_expense(self, description: str, value: int) -> Validation:
            ...
    ```

2. Remove the direct `Service()` instantiation from each method body — services are now injected.

### File: `src/backend/injector_module.py`

**Changes needed:** Register `BusinessService` as a singleton:
```python
@singleton
def provide_business_service(
    self,
    freight_service: FreightDistributionService,
    xml_service: XmlImportService,
    validation_service: ValidationService,
) -> BusinessService:
    return BusinessService(
        freight_service=freight_service,
        xml_service=xml_service,
        validation_service=validation_service,
    )
```

### File: `src/frontend/views/order_edit/order_items_card.py`

**Changes needed:**
1. Accept `BusinessService` as a constructor parameter (replacing `FreightDistributionService`):
    ```python
    def __init__(
        self,
        parent: QWidget | None = None,
        business_service: BusinessService | None = None,
    ) -> None:
    ```
2. Store `self._business_service = business_service`
3. In `_on_distribute_freight()`: replace `distribute_freight(order_data)` with `self._business_service.distribute_freight(order_data)`

### File: `src/frontend/views/order_edit/order_edit_dialog.py`

**Changes needed:**
1. Accept `BusinessService` as a constructor parameter (replacing the separate `FreightDistributionService` injection).
2. Pass `self._business_service` to `OrderItemsCard(self, business_service=self._business_service)`.

---

## Phase 5: Frontend Constructor Injection — Bridge Classes & Factories

Each frontend class that currently calls bridge functions directly will instead receive its **bridge class instances** and **dialog factory functions** via constructor injection.

### View Classes

#### `ProductListView` — `src/frontend/views/product_list.py`

**Current `__init__`:** `def __init__(self, parent: QWidget | None = None) -> None`

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    product_bridge: ProductBridge | None = None,
) -> None:
```

**Internal changes:**
- Store `self._product_bridge = product_bridge`
- Validate in `__init__`: if `product_bridge is None`, raise `RuntimeError` with DI instruction
- In `_refresh_page()`: replace `fetch_products(self._current_page, ...)` with `self._product_bridge.fetch_products(self._current_page, ...)`

#### `OrderEditListView` — `src/frontend/views/order_edit/order_edit_list.py`

**Current `__init__`:** `def __init__(self, parent: QWidget | None = None) -> None`

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    order_summary_bridge: OrderSummaryBridge | None = None,
    order_bridge: OrderBridge | None = None,
    xml_service: XmlImportService | None = None,
    order_edit_dialog_factory: Callable[[str | None, Order | None], OrderEditDialog] | None = None,
    nfe_search_dialog_factory: Callable[[], NfeSearchDialog] | None = None,
) -> None:
```

**Internal changes:**
- Store all injected dependencies as instance attributes
- In `fetch_orders()`: replace `fetch_order_summaries(month)` with `self._order_summary_bridge.fetch_order_summaries(month)`
- In `_on_edit_clicked()` and `_on_add_clicked()`: use `self._order_edit_dialog_factory(order_id)` / `self._order_edit_dialog_factory()` instead of direct `OrderEditDialog(self, order_id=...)` construction
- In `_on_import_xml_clicked()`: replace `import_xml(file_path)` with `import_xml(self._xml_service, file_path)`
- In `_on_consultar_xml_clicked()`: use `self._nfe_search_dialog_factory()` instead of direct `NfeSearchDialog(self)` construction
- In `_on_nfe_result()`: replace `import_xml(xml_path)` with `import_xml(self._xml_service, xml_path)`

#### `ExpenseListView` — `src/frontend/views/expense_list.py`

**Current `__init__`:** `def __init__(self, parent: QWidget | None = None) -> None`

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    expense_bridge: ExpenseBridge | None = None,
    expense_edit_dialog_factory: Callable[[str], ExpenseEditDialog] | None = None,
) -> None:
```

**Internal changes:**
- Store `self._expense_bridge` and `self._expense_edit_dialog_factory`
- In `fetch_expenses()`: replace `fetch_expenses_for_month(month)` with `self._expense_bridge.fetch_expenses_for_month(month)`
- In `_on_edit()`: use `self._expense_edit_dialog_factory(month)` instead of `ExpenseEditDialog(self, month=month)`

#### `CertificateStatusView` — `src/frontend/views/certificate_status/certificate_status.py`

**Current `__init__`:** `def __init__(self, parent: QWidget | None = None) -> None`

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    certificate_bridge: CertificateBridge | None = None,
    certificate_change_dialog_factory: Callable[[], CertificateChangeDialog] | None = None,
) -> None:
```

**Internal changes:**
- Store `self._certificate_bridge` and `self._certificate_change_dialog_factory`
- In `_load_certificate()`: replace `fetch_certificate_info()` with `self._certificate_bridge.fetch_certificate_info()`
- In `_on_change_clicked()`: use `self._certificate_change_dialog_factory()` instead of `CertificateChangeDialog(self)`

### Dialog Classes

Dialogs are **non-singleton** — they are constructed on-demand. They receive their dependencies via constructor.

#### `OrderEditDialog` — `src/frontend/views/order_edit/order_edit_dialog.py`

**Current `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    order_id: str | None = None,
    order: Order | None = None,
) -> None:
```

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    order_id: str | None = None,
    order: Order | None = None,
    order_bridge: OrderBridge | None = None,
    business_service: BusinessService | None = None,
) -> None:
```

**Internal changes:**
- Store `self._order_bridge` and `self._business_service`
- Validate in `__init__`: if either is `None`, raise `RuntimeError`
- In the `elif order_id:` branch: replace `fetch_order_by_id(order_id)` with `self._order_bridge.fetch_order_by_id(order_id)`
- In `_on_save()`: replace `save_single_order(order_data)` with `self._order_bridge.save_single_order(order_data)`
- Pass `self._business_service` to `OrderItemsCard(self, business_service=self._business_service)`

#### `ExpenseEditDialog` — `src/frontend/views/expense_edit/expense_edit_dialog.py`

**Current `__init__`:**
```python
def __init__(self, parent: QWidget, month: str) -> None:
```

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget,
    month: str,
    expense_bridge: ExpenseBridge | None = None,
) -> None:
```

**Internal changes:**
- Store `self._expense_bridge`
- Validate in `__init__`: if `expense_bridge is None`, raise `RuntimeError`
- In `__init__`: replace `fetch_expenses_for_month(self._month)` with `self._expense_bridge.fetch_expenses_for_month(self._month)`
- In `_on_save()`: replace `save_expenses(expenses_list, self._month)` with `self._expense_bridge.save_expenses(expenses_list, self._month)`

#### `CertificateChangeDialog` — `src/frontend/views/certificate_status/certificate_change_dialog.py`

**Current `__init__`:** `def __init__(self, parent: QWidget | None = None) -> None`

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    certificate_bridge: CertificateBridge | None = None,
) -> None:
```

**Internal changes:**
- Store `self._certificate_bridge`
- Validate in `__init__`: if `certificate_bridge is None`, raise `RuntimeError`
- In `_on_save()`: replace `save_certificate_from_pfx(self._pfx_path, ...)` with `self._certificate_bridge.save_certificate_from_pfx(self._pfx_path, ...)`

#### `NfeSearchDialog` — `src/frontend/nfe_search_dialog.py`

**Current `__init__`:** `def __init__(self, parent: QWidget | None = None) -> None`

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    nfe_bridge: NfeBridge | None = None,
) -> None:
```

**Internal changes:**
- Store `self._nfe_bridge`
- Validate in `__init__`: if `nfe_bridge is None`, raise `RuntimeError`
- In `_start_worker()`: replace `NfeSearchWorker(nfe_key)` with `NfeSearchWorker(nfe_key, self._nfe_bridge)` (worker also needs the bridge — see below).

#### `NfeSearchWorker` — `src/frontend/workers/nfe_search_worker.py`

**Current `__init__`:** `def __init__(self, nfe_key: str, /) -> None`

**New `__init__`:**
```python
def __init__(
    self,
    nfe_key: str,
    /,
    nfe_bridge: NfeBridge | None = None,
) -> None:
```

**Internal changes:**
- Store `self._nfe_bridge`
- Validate in `__init__`: if `nfe_bridge is None`, raise `RuntimeError`
- In `start_search()`: replace `search_nfe_key(self._nfe_key)` with `self._nfe_bridge.search_nfe_key(self._nfe_key)`

---

### Classes NOT Requiring DI

These classes have **no bridge/service dependencies** and should **not** be registered in the DI container:

| Class | File | Reason |
|-------|------|--------|
| `OrderHeaderCard` | `src/frontend/views/order_edit/order_header_card.py` | Only uses `TextField`, `Card`, `cents_to_display`, `iso_to_br_date` — all stateless utilities |
| `ProductRowWidget` | `src/frontend/views/order_edit/product_row_widget.py` | Only uses `ProductInput`, `cents_to_display`, `parse_currency_to_cents`, `svg_to_pixmap` — all stateless |
| `ExpenseItemsCard` | `src/frontend/views/expense_edit/expense_items_card.py` | Only uses `ExpenseInput`, `cents_to_display`, `parse_currency_to_cents` — all stateless |
| `ExpenseRowWidget` | `src/frontend/views/expense_edit/expense_row_widget.py` | Only uses `ExpenseInput`, `ExpenseOutput`, `cents_to_display`, `parse_currency_to_cents` — all stateless |
| `NavigationBar` | `src/frontend/components/navbar.py` | Only uses `NAV_GROUPS` from constants |
| `MonthFilter` | `src/frontend/components/month_filter.py` | Pure widget, no data dependencies |
| `Card` | `src/frontend/components/card.py` | Pure widget, no data dependencies |
| `TextField` | `src/frontend/components/text_field.py` | Pure widget, no data dependencies |

**Note about `OrderItemsCard`:** This class is **NOT** in the "no DI" list. It calls `distribute_freight()` from `business.py`. Since `business.py` is now a `BusinessService` class, `OrderItemsCard` must receive `BusinessService` via constructor injection. Because `OrderItemsCard` is created inside `OrderEditDialog` (line 45 of `order_edit_dialog.py`), the dialog must pass the service to the card. The dialog receives `BusinessService` via DI and forwards it to `OrderItemsCard`.

---

## Phase 6: Dialog Factory Registration in `InjectorModule`

Since `injector.get()` doesn't support passing runtime arguments (like `order_id`, `month`), we use **factory functions** registered in DI. The factory resolves structural dependencies (bridge classes, services) from the injector and accepts runtime parameters.

### Factory Registrations

Each factory is a `@provider` method in `InjectorModule` that creates the dialog with all DI-wired dependencies, using lazy imports to avoid circular dependencies.

#### Factory: `OrderEditDialog`

```python
@provider
def provide_order_edit_dialog_factory(
    self,
    injector: Injector,
) -> Callable[[str | None, Order | None], OrderEditDialog]:
    def factory(
        order_id: str | None = None,
        order: Order | None = None,
    ) -> OrderEditDialog:
        from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
        return OrderEditDialog(
            order_id=order_id,
            order=order,
            order_bridge=injector.get(OrderBridge),
            freight_service=injector.get(FreightDistributionService),
        )
    return factory
```

#### Factory: `ExpenseEditDialog`

```python
@provider
def provide_expense_edit_dialog_factory(
    self,
    injector: Injector,
) -> Callable[[str], ExpenseEditDialog]:
    def factory(month: str) -> ExpenseEditDialog:
        from frontend.views.expense_edit.expense_edit_dialog import ExpenseEditDialog
        return ExpenseEditDialog(
            month=month,
            expense_bridge=injector.get(ExpenseBridge),
        )
    return factory
```

#### Factory: `CertificateChangeDialog`

```python
@provider
def provide_certificate_change_dialog_factory(
    self,
    injector: Injector,
) -> Callable[[], CertificateChangeDialog]:
    def factory() -> CertificateChangeDialog:
        from frontend.views.certificate_status.certificate_change_dialog import CertificateChangeDialog
        return CertificateChangeDialog(
            certificate_bridge=injector.get(CertificateBridge),
        )
    return factory
```

#### Factory: `NfeSearchDialog`

```python
@provider
def provide_nfe_search_dialog_factory(
    self,
    injector: Injector,
) -> Callable[[], NfeSearchDialog]:
    def factory() -> NfeSearchDialog:
        from frontend.nfe_search_dialog import NfeSearchDialog
        return NfeSearchDialog(
            nfe_bridge=injector.get(NfeBridge),
        )
    return factory
```

### Apply factory pattern to all views

#### `OrderEditListView` — `_on_edit_clicked`, `_on_add_clicked`, `_on_consultar_xml_clicked`

```python
def _on_edit_clicked(self, order_id: str) -> None:
    dialog = self._order_edit_dialog_factory(order_id=order_id)
    dialog.setParent(self)
    dialog.order_saved.connect(self._on_order_saved)
    dialog.exec()

def _on_add_clicked(self) -> None:
    dialog = self._order_edit_dialog_factory()
    dialog.setParent(self)
    dialog.order_saved.connect(self._on_order_saved)
    dialog.exec()

def _on_consultar_xml_clicked(self) -> None:
    dialog = self._nfe_search_dialog_factory()
    dialog.setParent(self)
    dialog.nfe_result.connect(self._on_nfe_result)
    dialog.exec()
```

#### `ExpenseListView` — `_on_edit`

```python
def _on_edit(self) -> None:
    month: str = self.month_filter.get_month()
    if not month or not month.strip():
        return
    dialog = self._expense_edit_dialog_factory(month)
    dialog.setParent(self)
    dialog.expenses_saved.connect(self._on_expenses_saved)
    dialog.exec()
```

#### `CertificateStatusView` — `_on_change_clicked`

```python
def _on_change_clicked(self) -> None:
    dialog = self._certificate_change_dialog_factory()
    dialog.setParent(self)
    dialog.exec()
    self._load_certificate()
```

---

## Phase 7: Register View Factory Functions in `InjectorModule`

Since `injector.get()` doesn't support passing runtime arguments (like `parent: QWidget | None`), we use **factory functions** registered in DI for views — the same pattern already used for dialogs. Each view factory accepts a `parent` parameter and resolves all other dependencies (bridge classes, dialog factories) from the injector.

### Factory Registrations

Each factory is a `@provider` method in `InjectorModule` that creates the view with all DI-wired dependencies, using lazy imports to avoid circular dependencies.

#### Factory: `ProductListView`

```python
@provider
def provide_product_list_view_factory(
    self,
    injector: Injector,
) -> Callable[[QWidget | None], ProductListView]:
    def factory(parent: QWidget | None = None) -> ProductListView:
        from frontend.product_list import ProductListView
        return ProductListView(
            parent=parent,
            product_bridge=injector.get(ProductBridge),
        )
    return factory
```

#### Factory: `OrderEditListView`

```python
@provider
def provide_order_edit_list_view_factory(
    self,
    injector: Injector,
) -> Callable[[QWidget | None], OrderEditListView]:
    def factory(parent: QWidget | None = None) -> OrderEditListView:
        from frontend.views.order_edit.order_edit_list import OrderEditListView
        return OrderEditListView(
            parent=parent,
            order_summary_bridge=injector.get(OrderSummaryBridge),
            order_bridge=injector.get(OrderBridge),
            xml_service=injector.get(XmlImportService),
            order_edit_dialog_factory=injector.get(
                Callable[[str | None, Order | None], OrderEditDialog]
            ),
            nfe_search_dialog_factory=injector.get(
                Callable[[], NfeSearchDialog]
            ),
        )
    return factory
```

#### Factory: `ExpenseListView`

```python
@provider
def provide_expense_list_view_factory(
    self,
    injector: Injector,
) -> Callable[[QWidget | None], ExpenseListView]:
    def factory(parent: QWidget | None = None) -> ExpenseListView:
        from frontend.views.expense_list import ExpenseListView
        return ExpenseListView(
            parent=parent,
            expense_bridge=injector.get(ExpenseBridge),
            expense_edit_dialog_factory=injector.get(
                Callable[[str], ExpenseEditDialog]
            ),
        )
    return factory
```

#### Factory: `CertificateStatusView`

```python
@provider
def provide_certificate_status_view_factory(
    self,
    injector: Injector,
) -> Callable[[QWidget | None], CertificateStatusView]:
    def factory(parent: QWidget | None = None) -> CertificateStatusView:
        from frontend.views.certificate_status.certificate_status import CertificateStatusView
        return CertificateStatusView(
            parent=parent,
            certificate_bridge=injector.get(CertificateBridge),
            certificate_change_dialog_factory=injector.get(
                Callable[[], CertificateChangeDialog]
            ),
        )
    return factory
```

---

## Phase 8: `app.py` — Lazy View Construction via View Factories

### File: `src/frontend/app.py`

**Current state:** Creates views directly:
```python
product_list = ProductListView(self)
order_view = OrderEditListView(self)
cert_view = CertificateStatusView(self)
expense_view = ExpenseListView(self)
```

**New approach:** The `MainWindow` receives view factory functions in its constructor (injected by DI) and calls them with the appropriate `parent` argument.

**New `__init__`:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    product_list_view_factory: Callable[[QWidget | None], ProductListView] | None = None,
    order_edit_list_view_factory: Callable[[QWidget | None], OrderEditListView] | None = None,
    expense_list_view_factory: Callable[[QWidget | None], ExpenseListView] | None = None,
    certificate_status_view_factory: Callable[[QWidget | None], CertificateStatusView] | None = None,
) -> None:
    super().__init__(parent)
    self._product_list_view_factory = product_list_view_factory
    self._order_edit_list_view_factory = order_edit_list_view_factory
    self._expense_list_view_factory = expense_list_view_factory
    self._certificate_status_view_factory = certificate_status_view_factory
    self.setWindowTitle("Gessofer")
    self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    self._build_ui()
```

**Validation in `__init__`:** If any factory is `None`, raise `RuntimeError` with DI instruction.

**Changes to `_build_ui()`:**
```python
def _build_ui(self) -> None:
    self.nav_bar = NavigationBar(self)
    self.setMenuBar(self.nav_bar)

    # Initial view: ProductListView (non-singleton, constructed via factory)
    product_list = self._product_list_view_factory(self)
    self.setCentralWidget(product_list)

    self.nav_bar.item_clicked.connect(self._on_item_clicked)
```

**Changes to `_on_item_clicked()`:**
```python
def _on_item_clicked(self, label: str, group_title: str) -> None:
    if label == "Pedidos" and group_title == "Notas":
        view = self._product_list_view_factory(self)
        self.setCentralWidget(view)

    elif label == "Cadastrar" and group_title == "Notas":
        view = self._order_edit_list_view_factory(self)
        self.setCentralWidget(view)

    elif label == "Status" and group_title == "Certificado":
        view = self._certificate_status_view_factory(self)
        self.setCentralWidget(view)

    elif label == "Lista" and group_title == "Despesas":
        view = self._expense_list_view_factory(self)
        self.setCentralWidget(view)

    elif label == "Cadastrar" and group_title == "Despesas":
        QMessageBox.information(...)
```

**Dead code cleanup:** Remove the dead `build_layout()` method mentioned in AGENTS.md gotchas.

**Why non-singleton:** Each time a view is constructed, it starts fresh (new model, new pagination state, new signal connections). This is the correct behavior for a tab-like navigation where the user might switch back to a previously viewed tab and expect a clean state.

---

## Phase 9: `main.py` Changes

### File: `src/main.py`

**Current state:**
```python
window = MainWindow()
window.show()
```

**New state:**

```python
from di.injector_module import get_injector

injector = get_injector()
window = MainWindow(injector=injector)
window.show()
```

**Changes:**
1. Call `get_injector()` before creating `MainWindow`.
2. Pass the injector to `MainWindow(injector=injector)`.
3. The backup check code remains unchanged — it already calls `get_injector()` directly.

---

## DI Registration Summary

### Complete bindings table for `InjectorModule`:

| Binding | Type | Scope | Provider Method |
|---------|------|-------|-----------------|
| `Engine` | `Engine` | Singleton | `provide_engine` (existing) |
| `SessionFactory` | `Callable[[], Session]` | Singleton | `provide_session_factory` (existing) |
| `SaveOrderService` | `SaveOrderService` | Singleton | `provide_save_order_service` (existing) |
| `SaveExpenseService` | `SaveExpenseService` | Singleton | `provide_save_expense_service` (existing) |
| `NfeSearchService` | `NfeSearchService` | Singleton | `provide_nfe_search_service` (existing) |
| `BackupService` | `BackupService` | Singleton | `provide_backup_service` (existing) |
| `FetchHandler` | `FetchHandler` | Singleton | `provide_fetch_handler` |
| `SaveHandler` | `SaveHandler` | Singleton | `provide_save_handler` |
| `ExpenseFetchHandler` | `ExpenseFetchHandler` | Singleton | `provide_expense_fetch_handler` |
| `ExpenseSaveHandler` | `ExpenseSaveHandler` | Singleton | `provide_expense_save_handler` |
| `_CertificateHandler` | `_CertificateHandler` | Singleton | `provide_certificate_handler` |
| `FreightDistributionService` | `FreightDistributionService` | Singleton | `provide_freight_distribution_service` |
| `XmlImportService` | `XmlImportService` | Singleton | `provide_xml_import_service` |
| `ValidationService` | `ValidationService` | Singleton | `provide_validation_service` |
| `ProductBridge` | `ProductBridge` | Singleton | `provide_product_bridge` |
| `OrderBridge` | `OrderBridge` | Singleton | `provide_order_bridge` |
| `ExpenseBridge` | `ExpenseBridge` | Singleton | `provide_expense_bridge` |
| `NfeBridge` | `NfeBridge` | Singleton | `provide_nfe_bridge` |
| `CertificateBridge` | `CertificateBridge` | Singleton | `provide_certificate_bridge` |
| `OrderSummaryBridge` | `OrderSummaryBridge` | Singleton | `provide_order_summary_bridge` |
| Factory: `OrderEditDialog` | `Callable[[str\|None, Order\|None], OrderEditDialog]` | Singleton (factory) | `provide_order_edit_dialog_factory` |
| Factory: `ExpenseEditDialog` | `Callable[[str], ExpenseEditDialog]` | Singleton (factory) | `provide_expense_edit_dialog_factory` |
| Factory: `CertificateChangeDialog` | `Callable[[], CertificateChangeDialog]` | Singleton (factory) | `provide_certificate_change_dialog_factory` |
| Factory: `NfeSearchDialog` | `Callable[[], NfeSearchDialog]` | Singleton (factory) | `provide_nfe_search_dialog_factory` |
| `BusinessService` | `BusinessService` | Singleton | `provide_business_service` |
| Factory: `ProductListView` | `Callable[[QWidget | None], ProductListView]` | Singleton (factory) | `provide_product_list_view_factory` |
| Factory: `OrderEditListView` | `Callable[[QWidget | None], OrderEditListView]` | Singleton (factory) | `provide_order_edit_list_view_factory` |
| Factory: `ExpenseListView` | `Callable[[QWidget | None], ExpenseListView]` | Singleton (factory) | `provide_expense_list_view_factory` |
| Factory: `CertificateStatusView` | `Callable[[QWidget | None], CertificateStatusView]` | Singleton (factory) | `provide_certificate_status_view_factory` |

**Note:** Views (`ProductListView`, `OrderEditListView`, `ExpenseListView`, `CertificateStatusView`) are **NOT registered** directly in DI. They are constructed via their **factory functions** which resolve all constructor dependencies from the injector. This works because the factories call `injector.get()` for structural dependencies and accept `parent: QWidget | None` as a runtime parameter.

---

## Frontend Class Constructor Dependencies Summary

| View / Dialog | Injected Dependencies |
|---------------|----------------------|
| `ProductListView` | `ProductBridge` |
| `OrderEditListView` | `OrderSummaryBridge`, `OrderBridge`, `XmlImportService`, `OrderEditDialogFactory`, `NfeSearchDialogFactory` |
| `ExpenseListView` | `ExpenseBridge`, `ExpenseEditDialogFactory` |
| `CertificateStatusView` | `CertificateBridge`, `CertificateChangeDialogFactory` |
| `OrderEditDialog` | `OrderBridge`, `BusinessService` |
| `ExpenseEditDialog` | `ExpenseBridge` |
| `CertificateChangeDialog` | `CertificateBridge` |
| `NfeSearchDialog` | `NfeBridge` |
| `NfeSearchWorker` | `NfeBridge` |
| `OrderItemsCard` | `BusinessService` |

---

## Implementation Order

Execute changes in this sequence to maintain a working application at each step:

### Step 1: Register backend handlers in `injector_module.py`
- Add imports for `FetchHandler`, `SaveHandler`, `ExpenseFetchHandler`, `ExpenseSaveHandler`, `_CertificateHandler`
- Add `@singleton` provider methods for each
- **Test:** `python -c "from backend.injector_module import get_injector; i = get_injector(); print(i.get(FetchHandler))"`

### Step 2: Register business services in `injector_module.py`
- Add imports for `FreightDistributionService`, `XmlImportService`, `ValidationService`
- Add `@singleton` provider methods
- **Test:** Same as above, verify all singletons resolve

### Step 3: Transform `ProductBridge` — `src/bridge/product.py`
- Wrap module in `ProductBridge` class with constructor-injected `FetchHandler`
- Move helper functions as methods (keep standalone versions for cross-bridge reuse)
- Register `ProductBridge` singleton in `InjectorModule`
- **Test:** `injector.get(ProductBridge).fetch_products(1)` works

### Step 4: Transform `OrderBridge` — `src/bridge/order.py`
- Wrap module in `OrderBridge` class with constructor-injected `SaveHandler` + `session_factory`
- Register `OrderBridge` singleton in `InjectorModule`
- **Test:** `injector.get(OrderBridge).save_single_order(...)` works

### Step 5: Transform `ExpenseBridge` — `src/bridge/expense.py`
- Wrap module in `ExpenseBridge` class with constructor-injected handlers
- Register `ExpenseBridge` singleton in `InjectorModule`
- **Test:** `injector.get(ExpenseBridge).fetch_expenses_for_month(...)` works

### Step 6: Transform `NfeBridge`, `CertificateBridge`, `OrderSummaryBridge`
- Same pattern for each bridge module
- Register all three as singletons in `InjectorModule`
- **Test:** Each bridge resolves and its methods work

### Step 7: Update `bridge/__init__.py`
- Update `TYPE_CHECKING` imports to reference new class names
- Update `__all__` to reflect new public API

### Step 8: Transform `business.py` into `BusinessService` class
- Convert module-level functions into `BusinessService` class with constructor-injected services
- Register `BusinessService` singleton in `InjectorModule`
- **Test:** `injector.get(BusinessService).distribute_freight(...)` works

### Step 9: Update `OrderItemsCard` — accept `BusinessService` in constructor
- Use `self._business_service.distribute_freight(order_data)` instead of `distribute_freight(order_data)`

### Step 10: Update `OrderEditDialog` — accept bridge classes in constructor
- Accept `OrderBridge` and `BusinessService`
- Pass `business_service` to `OrderItemsCard`
- Use `self._order_bridge.fetch_order_by_id()` and `self._order_bridge.save_single_order()`

### Step 11: Update `ExpenseEditDialog` — accept `ExpenseBridge` in constructor
- Use `self._expense_bridge.fetch_expenses_for_month()` and `self._expense_bridge.save_expenses()`

### Step 12: Update `CertificateChangeDialog` — accept `CertificateBridge` in constructor
- Use `self._certificate_bridge.save_certificate_from_pfx()`

### Step 13: Update `NfeSearchDialog` and `NfeSearchWorker` — accept `NfeBridge` in constructor
- Worker receives `NfeBridge` via constructor, uses `self._nfe_bridge.search_nfe_key()`

### Step 14: Register dialog factories in `injector_module.py`
- Add factory provider methods for all dialogs
- **Test:** Factories resolve and create dialogs with correct dependencies

### Step 15: Register view factories in `injector_module.py`
- Add factory provider methods for all 4 views (`ProductListView`, `OrderEditListView`, `ExpenseListView`, `CertificateStatusView`)
- Each factory accepts `parent: QWidget | None` and resolves bridge classes, dialog factories from the injector
- **Test:** Factories resolve and create views with correct dependencies

### Step 16: Update `app.py`
- Accept view factory functions and dialog factory functions as constructor parameters
- Use view factories (`self._product_list_view_factory(self)`) instead of direct construction
- Replace direct dialog construction with factory calls
- Remove dead `build_layout()` method
- **Test:** Application launches, navigation works

### Step 17: Update `main.py`
- Create injector before `MainWindow`
- Pass injector to `MainWindow`
- **Test:** Full application launch

---

## Risks and Considerations

### Circular Import Risks
- **Frontend → Backend:** Frontend classes import bridge classes from `bridge`. Bridge imports from `backend`. This already works.
- **InjectorModule → Frontend:** We do **NOT** register frontend classes at module level in `InjectorModule`. We only register backend services/handlers/bridges and factory functions. Factory functions are in `injector_module.py` but they only import frontend classes inside the function body (lazy import), avoiding circular imports at module load time.
  - **Implementation detail:** In factory provider methods, import frontend classes inside the provider function body:
    ```python
    def provide_order_edit_dialog_factory(self, injector: Injector):
        from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
        # ... use OrderEditDialog inside the nested function
    ```

### Bridge Class Cross-Dependencies
- `OrderSummaryBridge` depends on `ProductBridge` (calls `fetch_orders_for_month`). `OrderBridge` needs `ProductBridge`'s helper methods. These are resolved naturally by DI — `injector.get(OrderSummaryBridge)` will first resolve `ProductBridge` as a dependency.
- **Implementation detail:** `OrderBridge.orm_product_to_dict()` should either import from `ProductBridge` or keep a standalone helper function in `bridge/product.py` to avoid circular imports between bridge classes.

### Thread Safety
- `NfeSearchWorker` runs in a background `QThread`. It receives `NfeBridge` via constructor. The bridge delegates to `NfeSearchService` which is a singleton and must be thread-safe. `NfeSearchService.search_and_save()` writes to disk and calls SEFAZ — it should be safe for concurrent calls (each call creates its own file path based on the key).

### Session Lifecycle
- Handlers create sessions per-operation via `session_factory()`. This is unchanged. `OrderBridge.fetch_order_by_id()` creates its own session internally — this is by design since it's a simple read that doesn't need a handler.

### Memory Management
- Views constructed via factory functions are owned by `QMainWindow.setCentralWidget()`. When the central widget is replaced, Qt's parent-child ownership model ensures the old widget is cleaned up.
- Dialogs are created, shown with `exec()`, and then go out of scope. Qt's parent-child model handles cleanup.

### Backward Compatibility
- All new constructor parameters use **`None`** as default values, validated in `__init__`:
    ```python
    def __init__(
        self,
        parent: QWidget | None = None,
        product_bridge: ProductBridge | None = None,
    ) -> None:
        super().__init__(parent)
        if product_bridge is None:
            raise RuntimeError(
                "ProductListView must be constructed via DI injector. "
                "Use injector.get(ProductListView)."
            )
        self._product_bridge = product_bridge
    ```
  This gives a clear error message if someone instantiates the class directly.

### `OrderItemsCard` — Real DI Dependency (Fixed)
- `OrderItemsCard` **does require DI** because `distribute_freight()` is now a method on `BusinessService`. The service flows: `InjectorModule` → `OrderEditDialog` (constructor) → `OrderItemsCard` (constructor). `OrderItemsCard` is created inside `OrderEditDialog.__init__()` (line 45), so the dialog passes the service to the card.

### Bridge Class Design — Thin Adapters
- Bridge classes are **thin adapters** that wrap handler/service logic. They should not contain business logic — that belongs in services. The bridge layer's responsibility is:
  1. ORM-to-dict conversion (helper methods)
  2. Error handling (try/except returning safe defaults)
  3. API surface for the frontend (method signatures that the frontend expects)

### Known Issues Not Addressed by This Plan
- The `supplier` filter bug in `search_products` (filters on `Product.NAME_NORMALIZED` instead of `Order.SUPPLIER_NORMALIZED`) — not fixed here.
- The `print(month)` debug statement in `order_repository.py` line 82 — not touched.
- The dead `build_layout()` method in `app.py` — removed as part of this plan's cleanup.

---

## Files to Create / Modify / Delete

### Files to Modify

| File | Changes |
|------|---------|
| `src/backend/injector_module.py` | Add 22 new provider methods (5 handlers + 3 services + 1 BusinessService + 6 bridge classes + 4 dialog factories + 4 view factories), add new imports |
| `src/bridge/product.py` | Transform into `ProductBridge` class with constructor-injected `FetchHandler`, helper methods, register singleton |
| `src/bridge/order.py` | Transform into `OrderBridge` class with constructor-injected `SaveHandler` + `session_factory`, register singleton |
| `src/bridge/expense.py` | Transform into `ExpenseBridge` class with constructor-injected handlers, register singleton |
| `src/bridge/nfe.py` | Transform into `NfeBridge` class with constructor-injected `NfeSearchService`, remove lazy singleton, register singleton |
| `src/bridge/certificate.py` | Transform into `CertificateBridge` class with constructor-injected `_CertificateHandler`, remove lazy singleton, register singleton |
| `src/bridge/order_summary.py` | Transform into `OrderSummaryBridge` class with constructor-injected `ProductBridge`, register singleton |
| `src/bridge/__init__.py` | Update `TYPE_CHECKING` imports for new class names, update `__all__` |
| `src/frontend/business.py` | Transform into `BusinessService` class with constructor-injected services, register singleton |
| `src/frontend/views/order_edit/order_items_card.py` | Accept `BusinessService` in constructor, use `self._business_service.distribute_freight()` |
| `src/frontend/views/order_edit/order_edit_dialog.py` | Accept `OrderBridge` + `BusinessService` in constructor, pass service to `OrderItemsCard`, use bridge methods |
| `src/frontend/views/order_edit/order_edit_list.py` | Accept `OrderSummaryBridge` + `OrderBridge` + `XmlImportService` + dialog factories in constructor, use bridge methods and factories |
| `src/frontend/views/product_list.py` | Accept `ProductBridge` in constructor, use bridge methods |
| `src/frontend/views/expense_list.py` | Accept `ExpenseBridge` + `ExpenseEditDialogFactory` in constructor |
| `src/frontend/views/expense_edit/expense_edit_dialog.py` | Accept `ExpenseBridge` in constructor, use bridge methods |
| `src/frontend/views/certificate_status/certificate_status.py` | Accept `CertificateBridge` + `CertificateChangeDialogFactory` in constructor |
| `src/frontend/views/certificate_status/certificate_change_dialog.py` | Accept `CertificateBridge` in constructor, use bridge methods |
| `src/frontend/nfe_search_dialog.py` | Accept `NfeBridge` in constructor, pass to `NfeSearchWorker` |
| `src/frontend/workers/nfe_search_worker.py` | Accept `NfeBridge` in constructor, use bridge methods |
| `src/frontend/app.py` | Accept view factory functions + dialog factory functions, use factories for views (`self._product_list_view_factory(self)`) and dialogs, remove dead `build_layout()` |
| `src/main.py` | Create injector, pass to `MainWindow` |

### Files NOT Modified
- `src/frontend/components/navbar.py` — Pure widget, no DI needed
- `src/frontend/components/month_filter.py` — Pure widget, no DI needed
- `src/frontend/components/card.py` — Pure widget, no DI needed
- `src/frontend/components/text_field.py` — Pure widget, no DI needed
- `src/frontend/views/order_edit/order_header_card.py` — No bridge dependencies
- `src/frontend/views/order_edit/product_row_widget.py` — No bridge dependencies
- `src/frontend/views/expense_edit/expense_items_card.py` — No bridge dependencies (only uses `ExpenseInput`, `cents_to_display`, `parse_currency_to_cents`)
- `src/frontend/views/expense_edit/expense_row_widget.py` — No bridge dependencies
- `src/frontend/constants.py` — `NAV_GROUPS` unchanged
- `src/frontend/util/validators.py` — Stateless utilities
- `src/frontend/util/icons.py` — Stateless utilities

### Files to Delete
- None. No files are removed except the dead code `build_layout()` method inside `app.py`.
