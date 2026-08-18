# Implementation Plan: Frontend DI — Required Dependencies, Named Factory Types, View Factories, Dialog Factories

## Summary

This plan restructures the frontend layer so that: (1) all view classes are constructed exclusively through **factory classes registered in the DI container**, (2) all dialog classes are constructed exclusively through **factory classes registered in the DI container**, (3) **every dependency parameter is mandatory** — no `"| None = None"` fallbacks anywhere, and (4) **factory types are named `Protocol` classes** rather than raw `Callable[[...], ...]` annotations. The entry point resolves factories from the injector by their named type and passes them to `MainWindow`, which uses them to create child views on demand.

## Files to Create / Modify

### `src/frontend/factories.py` (rewrite)

**Purpose:** Central registry of all view and dialog factory types and implementations. Defines `Protocol` classes for factory types, then provides concrete implementation classes that the DI container resolves.

**Key contents — Named Factory Protocol Classes (top of file):**
- `ProductListViewFactory` — Protocol: `(parent: QWidget) -> ProductListView`
- `OrderEditListViewFactory` — Protocol: `(parent: QWidget) -> OrderEditListView`
- `ExpenseListViewFactory` — Protocol: `(parent: QWidget) -> ExpenseListView`
- `CertificateStatusViewFactory` — Protocol: `(parent: QWidget) -> CertificateStatusView`
- `OrderEditDialogFactory` — Protocol: `(parent: QWidget, order_id: str | None, order: Order | None) -> OrderEditDialog`
- `ExpenseEditDialogFactory` — Protocol: `(parent: QWidget, month: str) -> ExpenseEditDialog`
- `CertificateChangeDialogFactory` — Protocol: `(parent: QWidget) -> CertificateChangeDialog`
- `NfeSearchDialogFactory` — Protocol: `(parent: QWidget) -> NfeSearchDialog`

**Key contents — Factory Implementation Classes:**
- `_ProductListViewFactoryImpl` — implements `ProductListViewFactory`; holds `ProductBridge` resolved from DI
- `_OrderEditListViewFactoryImpl` — implements `OrderEditListViewFactory`; holds `OrderBridge`, `OrderSummaryBridge`, `BusinessService`, `NfeBridge`, and inner dialog factories
- `_ExpenseListViewFactoryImpl` — implements `ExpenseListViewFactory`; holds `ExpenseBridge` and inner dialog factory
- `_CertificateStatusViewFactoryImpl` — implements `CertificateStatusViewFactory`; holds `CertificateBridge` and inner dialog factory
- `_OrderEditDialogFactoryImpl` — implements `OrderEditDialogFactory`; holds `OrderBridge`, `BusinessService`
- `_ExpenseEditDialogFactoryImpl` — implements `ExpenseEditDialogFactory`; holds `ExpenseBridge`
- `_CertificateChangeDialogFactoryImpl` — implements `CertificateChangeDialogFactory`; holds `CertificateBridge`
- `_NfeSearchDialogFactoryImpl` — implements `NfeSearchDialogFactory`; holds `NfeBridge`

**Key contents — Standalone factory functions (for convenience, not DI-registered):**
- `make_product_list_view(parent: QWidget) -> ProductListView`
- `make_order_edit_list_view(parent: QWidget) -> OrderEditListView`
- `make_expense_list_view(parent: QWidget) -> ExpenseListView`
- `make_certificate_status_view(parent: QWidget) -> CertificateStatusView`
- `make_order_edit_dialog(parent: QWidget, order_id: str | None, order: Order | None) -> OrderEditDialog`
- `make_expense_edit_dialog(parent: QWidget, month: str) -> ExpenseEditDialog`
- `make_certificate_change_dialog(parent: QWidget) -> CertificateChangeDialog`
- `make_nfe_search_dialog(parent: QWidget) -> NfeSearchDialog`

**Dependencies:** Imports view/dialog classes (lazy inside functions) and bridge/service classes (resolved via `get_injector()`).

## Files to Modify

---

### 1. `src/frontend/views/product_list.py` — ProductListView

**Current state:**
```python
def __init__(self, parent: QWidget | None = None, product_bridge: ProductBridge | None = None) -> None:
    self._product_bridge: ProductBridge | None = product_bridge
    # ...
    if self._product_bridge is not None:
        result = self._product_bridge.fetch_products(...)
    else:
        result = fetch_products(...)  # fallback to module-level function
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(self, parent: QWidget, product_bridge: ProductBridge) -> None:
  ```
  Both parameters are **required**. No fallbacks. No `| None = None`.
- **Remove** the `self._product_bridge: ProductBridge | None` type annotation — change to `self._product_bridge: ProductBridge`.
- **Remove** the `if self._product_bridge is not None: ... else: fetch_products(...)` fallback logic in `_refresh_page()`. Call `self._product_bridge.fetch_products(...)` unconditionally.
- **Remove** the `import fetch_products` from the module-level import (it was a backward-compatible re-export).

**Rationale:** The factory implementation (`_ProductListViewFactoryImpl`) will always provide a real `ProductBridge`. There is no scenario where it should be absent. Removing the fallback eliminates dead code paths and ensures the DI contract is enforced.

---

### 2. `src/frontend/views/order_edit/order_edit_list.py` — OrderEditListView

**Current state:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    order_bridge: OrderBridge | None = None,
    order_summary_bridge: OrderSummaryBridge | None = None,
    business_service: BusinessService | None = None,
    nfe_bridge: NfeBridge | None = None,
) -> None:
    self._order_bridge: OrderBridge | None = order_bridge
    self._order_summary_bridge: OrderSummaryBridge | None = order_summary_bridge
    self._business_service: BusinessService | None = business_service
    self._nfe_bridge: NfeBridge | None = nfe_bridge
    # ...
    if self._order_summary_bridge is not None:
        summaries = self._order_summary_bridge.fetch_order_summaries(month)
    else:
        summaries = fetch_order_summaries(month)
    # ...
    if self._business_service is not None:
        result = self._business_service.import_xml(...)
    else:
        result = import_xml(...)
    # ...
    if self._nfe_bridge is not None:
        result_path = self._nfe_bridge.search_nfe_key(xml_path)
    else:
        from bridge.nfe import search_nfe_key
        result_path = search_nfe_key(xml_path)
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      order_bridge: OrderBridge,
      order_summary_bridge: OrderSummaryBridge,
      business_service: BusinessService,
      nfe_bridge: NfeBridge,
      order_edit_dialog_factory: OrderEditDialogFactory,
      nfe_search_dialog_factory: NfeSearchDialogFactory,
  ) -> None:
  ```
  All parameters are **required**. No fallbacks. Uses named factory types instead of raw `Callable`.
- **Remove** the `| None` type annotations on all stored attributes.
- **Remove** all `if self._xxx is not None: ... else: fallback_function(...)` branches. Call the method/attribute unconditionally.
- **Replace** direct dialog construction with factory calls:
  - `_on_edit_clicked`: `dialog = self._order_edit_dialog_factory(self, order_id, None)`
  - `_on_add_clicked`: `dialog = self._order_edit_dialog_factory(self, None, None)`
  - `_on_consultar_xml_clicked`: `dialog = self._nfe_search_dialog_factory(self)`
- **Remove** module-level imports of backward-compatible functions (`fetch_order_summaries`, `import_xml`, `search_nfe_key`) — they are no longer needed.

**Rationale:** The factory implementation (`_OrderEditListViewFactoryImpl`) will always provide all dependencies. The fallback branches are dead code that masks missing DI wiring.

---

### 3. `src/frontend/views/order_edit/order_edit_dialog.py` — OrderEditDialog

**Current state:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    order_id: str | None = None,
    order: Order | None = None,
    order_bridge: OrderBridge | None = None,
    business_service: BusinessService | None = None,
) -> None:
    self._order_bridge = order_bridge
    self._business_service = business_service
    # ...
    elif order_id:
        assert self._order_bridge is not None  # ← assertion, not proper error
        order_data = self._order_bridge.fetch_order_by_id(order_id)
    # ...
    assert self._order_bridge is not None  # ← assertion in _on_save
    success = self._order_bridge.save_single_order(order_data)
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      order_id: str | None,
      order: Order | None,
      order_bridge: OrderBridge,
      business_service: BusinessService,
  ) -> None:
  ```
  `parent`, `order_bridge`, and `business_service` are **required**. `order_id` and `order` remain optional because they represent different construction modes (edit existing, create from parsed Order, create blank).
- **Remove** `self._order_bridge = order_bridge` fallback — store as `self._order_bridge: OrderBridge` (non-optional).
- **Remove** `self._business_service = business_service` fallback — store as `self._business_service: BusinessService`.
- **Remove** `assert self._order_bridge is not None` — the type system guarantees it's never None.
- **Replace** the `elif order_id:` branch: `order_data = self._order_bridge.fetch_order_by_id(order_id)` (no assert needed).
- **Replace** `_on_save`: `success = self._order_bridge.save_single_order(order_data)` (no assert needed).
- **Pass** `business_service` to `OrderItemsCard`: `self.items_card = OrderItemsCard(self, business_service=self._business_service)`.

**Rationale:** `order_id` and `order` are legitimately optional (they define the dialog's mode). But `order_bridge` and `business_service` are structural dependencies that must always be provided by the factory implementation (`_OrderEditDialogFactoryImpl`).

---

### 4. `src/frontend/views/order_edit/order_items_card.py` — OrderItemsCard

**Current state:**
```python
def __init__(
    self,
    parent: QWidget | None = None,
    business_service: BusinessService | None = None,
) -> None:
    self._business_service = business_service
    # ...
    result = self._business_service.distribute_freight(products_list)  # will crash if None
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      business_service: BusinessService,
  ) -> None:
  ```
  Both parameters are **required**.
- **Remove** `self._business_service = business_service` fallback — store as `self._business_service: BusinessService`.
- **Remove** the `business_service: BusinessService | None = None` from the `| None` annotation.

**Rationale:** `OrderItemsCard` always needs `BusinessService` for freight distribution. The factory implementation will provide it.

---

### 5. `src/frontend/views/expense_list.py` — ExpenseListView

**Current state:**
```python
def __init__(self, parent: QWidget | None = None, expense_bridge: ExpenseBridge | None = None) -> None:
    self._expense_bridge: ExpenseBridge | None = expense_bridge
    # ...
    if self._expense_bridge is not None:
        result = self._expense_bridge.fetch_expenses_for_month(month)
    else:
        result = fetch_expenses_for_month(month)
    # ...
    edit_dialog = ExpenseEditDialog(self, month=month)  # direct construction
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      expense_bridge: ExpenseBridge,
      expense_edit_dialog_factory: ExpenseEditDialogFactory,
  ) -> None:
  ```
  All parameters are **required**. Uses named factory type instead of raw `Callable`.
- **Remove** `self._expense_bridge: ExpenseBridge | None` — change to `self._expense_bridge: ExpenseBridge`.
- **Remove** the `if self._expense_bridge is not None: ... else: fetch_expenses_for_month(...)` fallback.
- **Replace** direct dialog construction: `dialog = self._expense_edit_dialog_factory(self, month)`.
- **Remove** the `_edit_dialog: ExpenseEditDialog | None = None` instance attribute — it's never used meaningfully.

**Rationale:** Same pattern as other views — the factory implementation (`_ExpenseListViewFactoryImpl`) provides all dependencies.

---

### 6. `src/frontend/views/expense_edit/expense_edit_dialog.py` — ExpenseEditDialog

**Current state:**
```python
def __init__(
    self,
    parent: QWidget,
    month: str,
    expense_bridge: ExpenseBridge | None = None,
) -> None:
    self._expense_bridge: ExpenseBridge | None = expense_bridge
    # ...
    if self._expense_bridge is not None:
        expenses_data = self._expense_bridge.fetch_expenses_for_month(self._month)
    else:
        expenses_data = fetch_expenses_for_month(self._month)
    # ...
    if self._expense_bridge is not None:
        success = self._expense_bridge.save_expenses(expenses_list, self._month)
    else:
        success = save_expenses(expenses_list, self._month)
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      month: str,
      expense_bridge: ExpenseBridge,
  ) -> None:
  ```
  All parameters are **required**.
- **Remove** `self._expense_bridge: ExpenseBridge | None` — change to `self._expense_bridge: ExpenseBridge`.
- **Remove** all `if self._expense_bridge is not None: ... else: fallback_function(...)` branches.
- **Remove** module-level imports of backward-compatible functions (`fetch_expenses_for_month`, `save_expenses`).

**Rationale:** `parent` and `month` are runtime parameters. `expense_bridge` is a structural dependency provided by the factory implementation (`_ExpenseEditDialogFactoryImpl`).

---

### 7. `src/frontend/views/certificate_status/certificate_status.py` — CertificateStatusView

**Current state:**
```python
def __init__(self, parent: QWidget | None = None, certificate_bridge: CertificateBridge | None = None) -> None:
    self._certificate_bridge: CertificateBridge | None = certificate_bridge
    # ...
    if self._certificate_bridge is not None:
        info = self._certificate_bridge.fetch_certificate_info()
    else:
        info = fetch_certificate_info()
    # ...
    dialog = CertificateChangeDialog(self)  # direct construction
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      certificate_bridge: CertificateBridge,
      certificate_change_dialog_factory: CertificateChangeDialogFactory,
  ) -> None:
  ```
  All parameters are **required**. Uses named factory type instead of raw `Callable`.
- **Remove** `self._certificate_bridge: CertificateBridge | None` — change to `self._certificate_bridge: CertificateBridge`.
- **Remove** the `if self._certificate_bridge is not None: ... else: fetch_certificate_info()` fallback.
- **Replace** direct dialog construction: `dialog = self._certificate_change_dialog_factory(self)`.
- **Remove** module-level import of backward-compatible `fetch_certificate_info`.

**Rationale:** Same pattern. The factory implementation (`_CertificateStatusViewFactoryImpl`) provides everything.

---

### 8. `src/frontend/views/certificate_status/certificate_change_dialog.py` — CertificateChangeDialog

**Current state:**
```python
def __init__(self, parent: QWidget | None = None, certificate_bridge: CertificateBridge | None = None) -> None:
    self._certificate_bridge: CertificateBridge | None = certificate_bridge
    # ...
    if self._certificate_bridge is not None:
        self._certificate_bridge.save_certificate_from_pfx(...)
    else:
        save_certificate_from_pfx(...)
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      certificate_bridge: CertificateBridge,
  ) -> None:
  ```
  Both parameters are **required**.
- **Remove** `self._certificate_bridge: CertificateBridge | None` — change to `self._certificate_bridge: CertificateBridge`.
- **Remove** the `if self._certificate_bridge is not None: ... else: save_certificate_from_pfx()` fallback.
- **Remove** module-level import of backward-compatible `save_certificate_from_pfx`.

**Rationale:** Certificate operations always need the bridge. The factory implementation (`_CertificateChangeDialogFactoryImpl`) provides it. No fallback scenario exists.

---

### 9. `src/frontend/nfe_search_dialog.py` — NfeSearchDialog

**Current state:**
```python
def __init__(self, parent: QWidget | None = None) -> None:
    self._worker: NfeSearchWorker | None = None
    self._thread: QThread | None = None
    # ...
    self._worker = NfeSearchWorker(nfe_key)  # direct instantiation, no DI
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      nfe_bridge: NfeBridge,
  ) -> None:
  ```
  Both parameters are **required**.
- **Add** `self._nfe_bridge: NfeBridge = nfe_bridge` instance attribute.
- **Modify** `_start_worker()` to pass the bridge to the worker:
  ```python
  self._worker = NfeSearchWorker(nfe_key, nfe_bridge=self._nfe_bridge)
  ```
- **Remove** `parent: QWidget | None = None` — parent is always provided by the factory implementation (`_NfeSearchDialogFactoryImpl`).

**Rationale:** NFe search always needs the bridge. The worker also needs it.

---

### 10. `src/frontend/workers/nfe_search_worker.py` — NfeSearchWorker

**Current state:**
```python
def __init__(self, nfe_key: str, /) -> None:
    self._nfe_key = nfe_key
    # ...
    xml_path = search_nfe_key(self._nfe_key)  # direct function call
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      nfe_key: str,
      /,
      nfe_bridge: NfeBridge,
  ) -> None:
  ```
  `nfe_bridge` is **required**.
- **Add** `self._nfe_bridge: NfeBridge = nfe_bridge`.
- **Replace** `search_nfe_key(self._nfe_key)` with `self._nfe_bridge.search_nfe_key(self._nfe_key)`.
- **Remove** module-level import of backward-compatible `search_nfe_key`.

**Rationale:** The worker runs in a background thread and needs the bridge to perform the SEFAZ call. The bridge is provided through the dialog → worker chain, which originates from the factory implementation.

---

### 11. `src/frontend/app.py` — MainWindow

**Current state:**
```python
def __init__(self, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    injector = get_injector()
    self._product_bridge = injector.get(ProductBridge)
    # ... resolves all bridges from injector directly ...
    self.nav_bar = NavigationBar(self)
    product_list = ProductListView(self, product_bridge=self._product_bridge)
    self.setCentralWidget(product_list)
    # ...
    def _on_item_clicked(self, label, group_title):
        product_list = ProductListView(self, product_bridge=self._product_bridge)
        self.setCentralWidget(product_list)
        order_view = OrderEditListView(self, order_bridge=..., order_summary_bridge=..., ...)
        self.setCentralWidget(order_view)
        # ... etc.
```

**Changes needed:**
- **Constructor signature →**
  ```python
  def __init__(
      self,
      parent: QWidget,
      product_list_view_factory: ProductListViewFactory,
      order_edit_list_view_factory: OrderEditListViewFactory,
      expense_list_view_factory: ExpenseListViewFactory,
      certificate_status_view_factory: CertificateStatusViewFactory,
  ) -> None:
  ```
  All parameters are **required**. Uses named factory Protocol types instead of raw `Callable`. **No DI container access** inside `MainWindow` — it receives factories, not bridges.
- **Remove** all `injector.get(...)` calls from `__init__`.
- **Store** all four factory parameters as instance attributes (all non-optional).
- **Remove** direct `ProductListView(self, product_bridge=...)` construction. Replace with `self._product_list_view_factory(self)`.
- **Remove** direct `OrderEditListView(self, order_bridge=..., ...)` construction. Replace with `self._order_edit_list_view_factory(self)`.
- **Remove** direct `CertificateStatusView(self, certificate_bridge=...)` construction. Replace with `self._certificate_status_view_factory(self)`.
- **Remove** direct `ExpenseListView(self, expense_bridge=...)` construction. Replace with `self._expense_list_view_factory(self)`.
- **Remove** the dead `build_layout()` method (lines 40-44, already noted in AGENTS.md gotchas).
- **Remove** imports of bridge classes, business service — they are no longer needed in this file.
- **Remove** `from injector_module import get_injector` import.
- **Add** import: `from frontend.factories import ProductListViewFactory, OrderEditListViewFactory, ExpenseListViewFactory, CertificateStatusViewFactory`.

**Rationale:** `MainWindow` should not know about DI internals. It receives named factory Protocol types and calls them. This is the core principle of the DI pattern. Named types are self-documenting and work cleanly with type checkers.

---

### 12. `src/main.py` — Entry Point

**Current state:**
```python
from frontend.app import MainWindow
# ...
get_injector()  # Ensures injector is created before MainWindow
window = MainWindow()
```

**Changes needed:**
- **New code:**
  ```python
  def main() -> None:
      # ... logging setup ...
      app = QApplication(sys.argv)
      app.setStyle("FluentUI3")
      app.setApplicationName("Gessofer")
      # ...
      injector = get_injector()
      
      product_list_view_factory: ProductListViewFactory = injector.get(ProductListViewFactory)
      order_edit_list_view_factory: OrderEditListViewFactory = injector.get(OrderEditListViewFactory)
      expense_list_view_factory: ExpenseListViewFactory = injector.get(ExpenseListViewFactory)
      certificate_status_view_factory: CertificateStatusViewFactory = injector.get(CertificateStatusViewFactory)
      
      window = MainWindow(
          parent=None,
          product_list_view_factory=product_list_view_factory,
          order_edit_list_view_factory=order_edit_list_view_factory,
          expense_list_view_factory=expense_list_view_factory,
          certificate_status_view_factory=certificate_status_view_factory,
      )
      window.show()
      # ... backup check ...
  ```
- **Add imports:** `from injector_module import get_injector`, `from frontend.factories import ProductListViewFactory, OrderEditListViewFactory, ExpenseListViewFactory, CertificateStatusViewFactory`, `from PySide6.QtWidgets import QWidget`.

**Rationale:** The entry point is the composition root. It creates the injector, resolves all factory Protocol types by their **named class** (not raw `Callable`), and constructs `MainWindow` with them. Using named types makes the DI resolution explicit and type-safe.

---

### 13. `src/frontend/factories.py` — Complete Rewrite

**Current state:** Factory functions exist but they: (a) accept `| None = None` fallbacks, (b) don't resolve dependencies from DI, (c) just forward parameters to constructors.

**Changes needed — complete rewrite using Protocol classes + implementation wrappers:**

```python
from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QWidget

from bridge.certificate import CertificateBridge
from bridge.expense import ExpenseBridge
from bridge.nfe import NfeBridge
from bridge.order import OrderBridge
from bridge.order_summary import OrderSummaryBridge
from bridge.product import ProductBridge
from backend.business import BusinessService
from frontend.nfe_search_dialog import NfeSearchDialog
from frontend.views.certificate_status.certificate_change_dialog import CertificateChangeDialog
from frontend.views.certificate_status.certificate_status import CertificateStatusView
from frontend.views.expense_edit.expense_edit_dialog import ExpenseEditDialog
from frontend.views.expense_list import ExpenseListView
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from frontend.views.order_edit.order_edit_list import OrderEditListView
from frontend.views.product_list import ProductListView
from models.order import Order


# ═══════════════════════════════════════════════════════════════════
# Named Factory Protocol Types
# ═══════════════════════════════════════════════════════════════════


class ProductListViewFactory(Protocol):
    """Factory protocol for creating ProductListView instances."""

    def __call__(self, parent: QWidget) -> ProductListView: ...


class OrderEditListViewFactory(Protocol):
    """Factory protocol for creating OrderEditListView instances."""

    def __call__(self, parent: QWidget) -> OrderEditListView: ...


class ExpenseListViewFactory(Protocol):
    """Factory protocol for creating ExpenseListView instances."""

    def __call__(self, parent: QWidget) -> ExpenseListView: ...


class CertificateStatusViewFactory(Protocol):
    """Factory protocol for creating CertificateStatusView instances."""

    def __call__(self, parent: QWidget) -> CertificateStatusView: ...


class OrderEditDialogFactory(Protocol):
    """Factory protocol for creating OrderEditDialog instances."""

    def __call__(
            self, parent: QWidget, order_id: str | None, order: Order | None
    ) -> OrderEditDialog: ...


class ExpenseEditDialogFactory(Protocol):
    """Factory protocol for creating ExpenseEditDialog instances."""

    def __call__(self, parent: QWidget, month: str) -> ExpenseEditDialog: ...


class CertificateChangeDialogFactory(Protocol):
    """Factory protocol for creating CertificateChangeDialog instances."""

    def __call__(self, parent: QWidget) -> CertificateChangeDialog: ...


class NfeSearchDialogFactory(Protocol):
    """Factory protocol for creating NfeSearchDialog instances."""

    def __call__(self, parent: QWidget) -> NfeSearchDialog: ...


# ═══════════════════════════════════════════════════════════════════
# Factory Implementation Classes (registered in DI container)
# ═══════════════════════════════════════════════════════════════════


class _ProductListViewFactoryImpl:
    """Concrete implementation of ProductListViewFactory."""

    def __init__(self, product_bridge: ProductBridge) -> None:
        self._product_bridge = product_bridge

    def __call__(self, parent: QWidget) -> ProductListView:
        return ProductListView(parent=parent, product_bridge=self._product_bridge)


class _OrderEditDialogFactoryImpl:
    """Concrete implementation of OrderEditDialogFactory."""

    def __init__(
            self,
            order_bridge: OrderBridge,
            business_service: BusinessService,
    ) -> None:
        self._order_bridge = order_bridge
        self._business_service = business_service

    def __call__(
            self, parent: QWidget, order_id: str | None, order: Order | None
    ) -> OrderEditDialog:
        return OrderEditDialog(
            parent=parent,
            order_id=order_id,
            order=order,
            order_bridge=self._order_bridge,
            business_service=self._business_service,
        )


class _NfeSearchDialogFactoryImpl:
    """Concrete implementation of NfeSearchDialogFactory."""

    def __init__(self, nfe_bridge: NfeBridge) -> None:
        self._nfe_bridge = nfe_bridge

    def __call__(self, parent: QWidget) -> NfeSearchDialog:
        return NfeSearchDialog(parent=parent, nfe_bridge=self._nfe_bridge)


class _ExpenseEditDialogFactoryImpl:
    """Concrete implementation of ExpenseEditDialogFactory."""

    def __init__(self, expense_bridge: ExpenseBridge) -> None:
        self._expense_bridge = expense_bridge

    def __call__(self, parent: QWidget, month: str) -> ExpenseEditDialog:
        return ExpenseEditDialog(
            parent=parent,
            month=month,
            expense_bridge=self._expense_bridge,
        )


class _CertificateChangeDialogFactoryImpl:
    """Concrete implementation of CertificateChangeDialogFactory."""

    def __init__(self, certificate_bridge: CertificateBridge) -> None:
        self._certificate_bridge = certificate_bridge

    def __call__(self, parent: QWidget) -> CertificateChangeDialog:
        return CertificateChangeDialog(
            parent=parent,
            certificate_bridge=self._certificate_bridge,
        )


class _OrderEditListViewFactoryImpl:
    """Concrete implementation of OrderEditListViewFactory."""

    def __init__(
            self,
            order_bridge: OrderBridge,
            order_summary_bridge: OrderSummaryBridge,
            business_service: BusinessService,
            nfe_bridge: NfeBridge,
            order_edit_dialog_factory: OrderEditDialogFactory,
            nfe_search_dialog_factory: NfeSearchDialogFactory,
    ) -> None:
        self._order_bridge = order_bridge
        self._order_summary_bridge = order_summary_bridge
        self._business_service = business_service
        self._nfe_bridge = nfe_bridge
        self._order_edit_dialog_factory = order_edit_dialog_factory
        self._nfe_search_dialog_factory = nfe_search_dialog_factory

    def __call__(self, parent: QWidget) -> OrderEditListView:
        return OrderEditListView(
            parent=parent,
            order_bridge=self._order_bridge,
            order_summary_bridge=self._order_summary_bridge,
            business_service=self._business_service,
            nfe_bridge=self._nfe_bridge,
            order_edit_dialog_factory=self._order_edit_dialog_factory,
            nfe_search_dialog_factory=self._nfe_search_dialog_factory,
        )


class _ExpenseListViewFactoryImpl:
    """Concrete implementation of ExpenseListViewFactory."""

    def __init__(
            self,
            expense_bridge: ExpenseBridge,
            expense_edit_dialog_factory: ExpenseEditDialogFactory,
    ) -> None:
        self._expense_bridge = expense_bridge
        self._expense_edit_dialog_factory = expense_edit_dialog_factory

    def __call__(self, parent: QWidget) -> ExpenseListView:
        return ExpenseListView(
            parent=parent,
            expense_bridge=self._expense_bridge,
            expense_edit_dialog_factory=self._expense_edit_dialog_factory,
        )


class _CertificateStatusViewFactoryImpl:
    """Concrete implementation of CertificateStatusViewFactory."""

    def __init__(
            self,
            certificate_bridge: CertificateBridge,
            certificate_change_dialog_factory: CertificateChangeDialogFactory,
    ) -> None:
        self._certificate_bridge = certificate_bridge
        self._certificate_change_dialog_factory = certificate_change_dialog_factory

    def __call__(self, parent: QWidget) -> CertificateStatusView:
        return CertificateStatusView(
            parent=parent,
            certificate_bridge=self._certificate_bridge,
            certificate_change_dialog_factory=self._certificate_change_dialog_factory,
        )


# ═══════════════════════════════════════════════════════════════════
# Standalone factory functions (for convenience, not DI-registered)
# ═══════════════════════════════════════════════════════════════════


def make_product_list_view(parent: QWidget) -> ProductListView:
    """Create a ProductListView with all dependencies resolved from DI."""
    from injector_module import get_injector
    injector = get_injector()
    product_bridge: ProductBridge = injector.get(ProductBridge)
    return ProductListView(parent=parent, product_bridge=product_bridge)


def make_order_edit_list_view(parent: QWidget) -> OrderEditListView:
    """Create an OrderEditListView with all dependencies resolved from DI."""
    from injector_module import get_injector
    injector = get_injector()
    return OrderEditListView(
        parent=parent,
        order_bridge=injector.get(OrderBridge),
        order_summary_bridge=injector.get(OrderSummaryBridge),
        business_service=injector.get(BusinessService),
        nfe_bridge=injector.get(NfeBridge),
        order_edit_dialog_factory=_make_order_edit_dialog_factory(injector),
        nfe_search_dialog_factory=_make_nfe_search_dialog_factory(injector),
    )


def make_expense_list_view(parent: QWidget) -> ExpenseListView:
    """Create an ExpenseListView with all dependencies resolved from DI."""
    from injector_module import get_injector
    injector = get_injector()
    return ExpenseListView(
        parent=parent,
        expense_bridge=injector.get(ExpenseBridge),
        expense_edit_dialog_factory=_make_expense_edit_dialog_factory(injector),
    )


def make_certificate_status_view(parent: QWidget) -> CertificateStatusView:
    """Create a CertificateStatusView with all dependencies resolved from DI."""
    from injector_module import get_injector
    injector = get_injector()
    return CertificateStatusView(
        parent=parent,
        certificate_bridge=injector.get(CertificateBridge),
        certificate_change_dialog_factory=_make_certificate_change_dialog_factory(injector),
    )


def make_order_edit_dialog(
        parent: QWidget, order_id: str | None = None, order: Order | None = None
) -> OrderEditDialog:
    """Create an OrderEditDialog for editing an existing order or creating a new one."""
    from injector_module import get_injector
    injector = get_injector()
    return OrderEditDialog(
        parent=parent,
        order_id=order_id,
        order=order,
        order_bridge=injector.get(OrderBridge),
        business_service=injector.get(BusinessService),
    )


def make_expense_edit_dialog(parent: QWidget, month: str) -> ExpenseEditDialog:
    """Create an ExpenseEditDialog for editing expenses of a given month."""
    from injector_module import get_injector
    injector = get_injector()
    return ExpenseEditDialog(
        parent=parent,
        month=month,
        expense_bridge=injector.get(ExpenseBridge),
    )


def make_certificate_change_dialog(parent: QWidget) -> CertificateChangeDialog:
    """Create a CertificateChangeDialog for selecting a new PFX certificate."""
    from injector_module import get_injector
    injector = get_injector()
    return CertificateChangeDialog(
        parent=parent,
        certificate_bridge=injector.get(CertificateBridge),
    )


def make_nfe_search_dialog(parent: QWidget) -> NfeSearchDialog:
    """Create an NfeSearchDialog for consulting an NFe via SEFAZ."""
    from injector_module import get_injector
    injector = get_injector()
    return NfeSearchDialog(
        parent=parent,
        nfe_bridge=injector.get(NfeBridge),
    )


# ── Inner factory helpers (for standalone functions) ───────────────


def _make_order_edit_dialog_factory(
        injector: "Injector",
) -> OrderEditDialogFactory:
    """Create an OrderEditDialogFactory that captures DI-resolved deps."""
    from injector_module import get_injector
    order_bridge: OrderBridge = injector.get(OrderBridge)
    business_service: BusinessService = injector.get(BusinessService)

    def factory(
            parent: QWidget, order_id: str | None = None, order: Order | None = None
    ) -> OrderEditDialog:
        return OrderEditDialog(
            parent=parent,
            order_id=order_id,
            order=order,
            order_bridge=order_bridge,
            business_service=business_service,
        )

    return factory  # type: ignore[return-value]


def _make_nfe_search_dialog_factory(
        injector: "Injector",
) -> NfeSearchDialogFactory:
    """Create an NfeSearchDialogFactory that captures DI-resolved deps."""
    from injector_module import get_injector
    nfe_bridge: NfeBridge = injector.get(NfeBridge)

    def factory(parent: QWidget) -> NfeSearchDialog:
        return NfeSearchDialog(
            parent=parent,
            nfe_bridge=nfe_bridge,
        )

    return factory  # type: ignore[return-value]


def _make_expense_edit_dialog_factory(
        injector: "Injector",
) -> ExpenseEditDialogFactory:
    """Create an ExpenseEditDialogFactory that captures DI-resolved deps."""
    from injector_module import get_injector
    expense_bridge: ExpenseBridge = injector.get(ExpenseBridge)

    def factory(parent: QWidget, month: str) -> ExpenseEditDialog:
        return ExpenseEditDialog(
            parent=parent,
            month=month,
            expense_bridge=expense_bridge,
        )

    return factory  # type: ignore[return-value]


def _make_certificate_change_dialog_factory(
        injector: "Injector",
) -> CertificateChangeDialogFactory:
    """Create a CertificateChangeDialogFactory that captures DI-resolved deps."""
    from injector_module import get_injector
    certificate_bridge: CertificateBridge = injector.get(CertificateBridge)

    def factory(parent: QWidget) -> CertificateChangeDialog:
        return CertificateChangeDialog(
            parent=parent,
            certificate_bridge=certificate_bridge,
        )

    return factory  # type: ignore[return-value]
```

**Key architectural decisions:**

1. **Protocol classes at the top** — all 8 factory protocols are defined first, making them the public contract. They are importable by any module that needs to type-annotate a factory parameter.

2. **Implementation classes** — each Protocol has a corresponding `_XxxFactoryImpl` class that implements `__call__`. These classes hold structural dependencies (bridges, services) as instance attributes, resolved once at construction time. The DI container resolves these implementation classes and their transitive dependencies.

3. **Standalone functions** — convenience functions like `make_product_list_view()` are provided for testing or ad-hoc use. They call `get_injector()` internally. They are **not** registered in the DI container.

4. **Inner helper functions** — `_make_*_dialog_factory()` functions create closure-based dialog factories for use inside view factories. They capture DI-resolved dependencies in closures. These are used by the standalone functions, not by the DI-registered implementation classes.

**Dependencies:** Imports all view/dialog classes, bridge classes, and business service. Uses `get_injector()` inside standalone functions and inner helpers to resolve structural dependencies.

---

### 14. `src/injector_module.py` — Register Factory Implementation Classes

**Current state:** Already registers backend services, handlers, and bridge classes as singletons. Does NOT register view/dialog factories.

**Changes needed — register factory implementation classes as singletons:**

```python
# In InjectorModule, add these provider methods (at the end, after bridge providers):

@provider
@singleton
def provide_product_list_view_factory(
    self,
    product_bridge: ProductBridge,
) -> ProductListViewFactory:
    from frontend.factories import _ProductListViewFactoryImpl
    return _ProductListViewFactoryImpl(product_bridge=product_bridge)


@provider
@singleton
def provide_order_edit_dialog_factory(
    self,
    order_bridge: OrderBridge,
    business_service: BusinessService,
) -> OrderEditDialogFactory:
    from frontend.factories import _OrderEditDialogFactoryImpl
    return _OrderEditDialogFactoryImpl(
        order_bridge=order_bridge,
        business_service=business_service,
    )


@provider
@singleton
def provide_nfe_search_dialog_factory(
    self,
    nfe_bridge: NfeBridge,
) -> NfeSearchDialogFactory:
    from frontend.factories import _NfeSearchDialogFactoryImpl
    return _NfeSearchDialogFactoryImpl(nfe_bridge=nfe_bridge)


@provider
@singleton
def provide_expense_edit_dialog_factory(
    self,
    expense_bridge: ExpenseBridge,
) -> ExpenseEditDialogFactory:
    from frontend.factories import _ExpenseEditDialogFactoryImpl
    return _ExpenseEditDialogFactoryImpl(expense_bridge=expense_bridge)


@provider
@singleton
def provide_certificate_change_dialog_factory(
    self,
    certificate_bridge: CertificateBridge,
) -> CertificateChangeDialogFactory:
    from frontend.factories import _CertificateChangeDialogFactoryImpl
    return _CertificateChangeDialogFactoryImpl(certificate_bridge=certificate_bridge)


@provider
@singleton
def provide_order_edit_list_view_factory(
    self,
    order_bridge: OrderBridge,
    order_summary_bridge: OrderSummaryBridge,
    business_service: BusinessService,
    nfe_bridge: NfeBridge,
    order_edit_dialog_factory: OrderEditDialogFactory,
    nfe_search_dialog_factory: NfeSearchDialogFactory,
) -> OrderEditListViewFactory:
    from frontend.factories import _OrderEditListViewFactoryImpl
    return _OrderEditListViewFactoryImpl(
        order_bridge=order_bridge,
        order_summary_bridge=order_summary_bridge,
        business_service=business_service,
        nfe_bridge=nfe_bridge,
        order_edit_dialog_factory=order_edit_dialog_factory,
        nfe_search_dialog_factory=nfe_search_dialog_factory,
    )


@provider
@singleton
def provide_expense_list_view_factory(
    self,
    expense_bridge: ExpenseBridge,
    expense_edit_dialog_factory: ExpenseEditDialogFactory,
) -> ExpenseListViewFactory:
    from frontend.factories import _ExpenseListViewFactoryImpl
    return _ExpenseListViewFactoryImpl(
        expense_bridge=expense_bridge,
        expense_edit_dialog_factory=expense_edit_dialog_factory,
    )


@provider
@singleton
def provide_certificate_status_view_factory(
    self,
    certificate_bridge: CertificateBridge,
    certificate_change_dialog_factory: CertificateChangeDialogFactory,
) -> CertificateStatusViewFactory:
    from frontend.factories import _CertificateStatusViewFactoryImpl
    return _CertificateStatusViewFactoryImpl(
        certificate_bridge=certificate_bridge,
        certificate_change_dialog_factory=certificate_change_dialog_factory,
    )
```

**Rationale:** The DI container resolves factory implementation classes by their **named Protocol type**. Each provider method takes structural dependencies as parameters (injected by the DI container) and constructs the corresponding implementation class. This ensures:

1. **Constructor injection** — dependencies are resolved by the DI container, not lazily inside `__call__`. This is cleaner and makes dependency graphs explicit.
2. **Protocol return types** — `main.py` calls `injector.get(ProductListViewFactory)` and gets back an object that implements `ProductListViewFactory.__call__`.
3. **Transitive resolution** — dialog factories (e.g., `OrderEditDialogFactory`) are resolved first, then passed as dependencies to view factories (e.g., `OrderEditListViewFactory`) that need them.
4. **No circular imports** — all factory class imports are inside `@provider` methods (lazy).

**Important:** Factory implementation providers must be registered **after** all their dependency singletons (bridges, services) are registered. Since `InjectorModule` processes providers in order, and view factories depend on bridge classes (which are registered earlier), this ordering is naturally satisfied. The dialog factories depend on bridges, and the view factories depend on both bridges and dialog factories — so dialog factory providers should come before view factory providers.

---

## Data Model Changes

None. No database schema changes, no new dataclasses, no DTO changes.

## API Changes

None. The bridge API surface (function signatures in bridge modules) is preserved. Only the frontend consumption of bridges changes — from module-level function calls to method calls on injected bridge instances.

## State Management Changes

None. Views are non-singletons constructed fresh each time a factory is called. Each construction starts with fresh internal state (new model, new pagination state, etc.).

## UI/UX Changes

None. No changes to layout, labels, or user interactions. All UI strings remain in Brazilian Portuguese.

## Testing Considerations

1. **Unit tests:** No test files exist yet. When tests are written, they should use the `in_memory_engine` fixture from `tests/conftest.py` and create factories manually (bypassing the injector) for isolation.

2. **Integration tests:** The `conftest.py` seed data (5 orders with 6 products) is sufficient for testing view factories.

3. **Edge cases to cover:**
   - Factory resolution fails if a singleton is missing — should raise a clear error.
   - Dialog factory called with both `order_id` and `order` — `order` should take precedence (existing behavior).
   - `OrderEditDialog` called with neither `order_id` nor `order` — should create a blank order (existing behavior, preserved).

## Risks and Considerations

### Circular Import Risk — HIGH
`injector_module.py` imports bridge classes. Bridge classes import backend services. Factory implementation classes in `factories.py` import view/dialog classes. View classes import bridge classes. This creates a potential cycle if `injector_module.py` imports from `factories.py` at module level.

**Mitigation:** All factory imports in `injector_module.py` are inside `@provider` methods (lazy). Factory implementation classes store dependencies as constructor parameters (injected by DI), not resolved inside `__call__`. No circular imports at module load time.

### Backward-Compatible Re-exports — MEDIUM
Bridge modules still have backward-compatible re-exports (e.g., `fetch_products()` in `bridge/product.py`). These delegate to the DI-registered bridge. They should be **removed** once all frontend code uses bridge instances directly.

**Mitigation:** Remove them as part of the view class changes (Step 15 below).

### `parent: QWidget` vs `parent: QWidget | None` — LOW
PySide6 allows `parent=None` (top-level window). The factory implementations take `parent: QWidget` (required), but in `main.py` we pass `parent=None` to `MainWindow`. This is a type inconsistency.

**Decision:** `MainWindow` takes `parent: QWidget | None = None` (it's the root window). All child views and dialogs take `parent: QWidget` (required) because they are always children of an existing widget. This is semantically correct — a factory should never create a top-level window without a parent.

**Implementation detail:** In `main.py`, pass `parent=None` explicitly to `MainWindow`'s constructor. All factory calls use `self` (the parent widget) as the argument.

### Named Factory Type Resolution in DI — LOW
The `injector` library resolves types by their class name. When `main.py` calls `injector.get(ProductListViewFactory)`, the injector finds the `@provider` method whose return type annotation is `ProductListViewFactory` (a `Protocol` class). The provider constructs a `_ProductListViewFactoryImpl` instance, which is structurally compatible with the `ProductListViewFactory` Protocol because it implements `__call__`.

**Mitigation:** Register each factory implementation class with a provider whose return type is the corresponding Protocol. The `injector` library uses structural typing for Protocols — it checks that the returned object implements `__call__` with the correct signature.

### `NfeSearchWorker` Thread Affinity — LOW
`NfeSearchWorker` is moved to a `QThread` via `moveToThread()`. Passing `NfeBridge` through the constructor is safe because `NfeBridge` methods are stateless (they call services that manage their own sessions).

**Mitigation:** No changes needed. The existing thread model already works.

## Implementation Order

Execute changes in this sequence to maintain a working application at each step. Each step should be tested before proceeding.

### Step 1: Rewrite `src/frontend/factories.py` — Define Protocols + Implementations
- Define all 8 factory `Protocol` classes at the top of the file.
- Create all 8 factory `_XxxFactoryImpl` implementation classes that implement the Protocols via `__call__`.
- Keep the existing standalone convenience functions (with corrected signatures — no `| None = None` fallbacks).
- **Test:** `python -c "from frontend.factories import ProductListViewFactory, _ProductListViewFactoryImpl; print('OK')"` — imports resolve without error.

### Step 2: Register factory implementations in `src/injector_module.py`
- Add `@provider` methods for all 8 factory types.
- Dialog factory providers come before view factory providers (because view factories depend on dialog factories).
- All providers use constructor injection (dependencies as method parameters).
- **Test:** `python -c "from injector_module import get_injector; i = get_injector(); print(i.get(ProductListViewFactory))"` — should resolve without error.

### Step 3: Update `ProductListView` — `src/frontend/views/product_list.py`
- Change constructor to require `parent: QWidget` and `product_bridge: ProductBridge`.
- Remove all `| None = None` fallbacks.
- Remove fallback `if/else` branches in `_refresh_page()`.
- **Test:** `_ProductListViewFactoryImpl(product_bridge).some_widget)` creates a working view.

### Step 4: Update `OrderEditListView` — `src/frontend/views/order_edit/order_edit_list.py`
- Change constructor to require all dependencies + named dialog factory types (`OrderEditDialogFactory`, `NfeSearchDialogFactory`).
- Remove all `| None = None` fallbacks.
- Replace direct dialog construction with factory calls.
- Remove fallback `if/else` branches.
- **Test:** Factory creates view; clicking "Editar" opens dialog via factory.

### Step 5: Update `OrderEditDialog` — `src/frontend/views/order_edit/order_edit_dialog.py`
- Change constructor: `parent: QWidget`, `order_bridge: OrderBridge`, `business_service: BusinessService` are required.
- `order_id` and `order` remain optional (they define construction mode).
- Remove `assert self._order_bridge is not None` — type system guarantees it.
- Pass `business_service` to `OrderItemsCard`.
- **Test:** Dialog opens for edit, creates, and XML import paths.

### Step 6: Update `OrderItemsCard` — `src/frontend/views/order_edit/order_items_card.py`
- Change constructor: `parent: QWidget`, `business_service: BusinessService` are required.
- **Test:** Freight distribution works.

### Step 7: Update `ExpenseListView` — `src/frontend/views/expense_list.py`
- Change constructor: require `parent`, `expense_bridge`, `expense_edit_dialog_factory: ExpenseEditDialogFactory`.
- Remove fallbacks.
- Replace direct dialog construction with factory call.
- **Test:** Expense list loads; "Editar" opens dialog via factory.

### Step 8: Update `ExpenseEditDialog` — `src/frontend/views/expense_edit/expense_edit_dialog.py`
- Change constructor: require `parent`, `month`, `expense_bridge`.
- Remove fallbacks.
- **Test:** Expense edit dialog loads and saves.

### Step 9: Update `CertificateStatusView` — `src/frontend/views/certificate_status/certificate_status.py`
- Change constructor: require `parent`, `certificate_bridge`, `certificate_change_dialog_factory: CertificateChangeDialogFactory`.
- Remove fallbacks.
- Replace direct dialog construction with factory call.
- **Test:** Certificate status loads; "Alterar certificado" opens dialog via factory.

### Step 10: Update `CertificateChangeDialog` — `src/frontend/views/certificate_status/certificate_change_dialog.py`
- Change constructor: require `parent`, `certificate_bridge`.
- Remove fallbacks.
- **Test:** Certificate change dialog saves.

### Step 11: Update `NfeSearchDialog` — `src/frontend/nfe_search_dialog.py`
- Change constructor: require `parent`, `nfe_bridge`.
- Pass bridge to `NfeSearchWorker`.
- **Test:** NFe search dialog opens and searches.

### Step 12: Update `NfeSearchWorker` — `src/frontend/workers/nfe_search_worker.py`
- Change constructor: require `nfe_bridge`.
- Use `self._nfe_bridge.search_nfe_key()` instead of module-level function.
- **Test:** Worker completes search successfully.

### Step 13: Update `MainWindow` — `src/frontend/app.py`
- Change constructor to accept 4 named factory Protocol types (no DI container access).
- Remove all `injector.get(...)` calls.
- Remove bridge/service imports.
- Remove dead `build_layout()` method.
- Use view factories to create child views.
- **Test:** Application launches; navigation switches views correctly.

### Step 14: Update `src/main.py` — Entry Point
- Create injector.
- Resolve view factory Protocol types from injector by **named class** (not `Callable`).
- Pass factories to `MainWindow`.
- **Test:** Full application launch.

### Step 15: Clean up backward-compatible re-exports in bridge modules
- Remove `_get_*_bridge()` functions and module-level re-export functions from all bridge modules.
- These were only needed when frontend called module-level functions.
- **Test:** Application still works; no import errors.

---

## Complete Dependency Map

### Singleton Bindings (in `InjectorModule`)

| Type | Scope | Provider |
|------|-------|----------|
| `Engine` | Singleton | `provide_engine` (existing) |
| `Callable[[], Session]` | Singleton | `provide_session_factory` (existing) |
| `SaveOrderService` | Singleton | `provide_save_order_service` (existing) |
| `SaveExpenseService` | Singleton | `provide_save_expense_service` (existing) |
| `NfeSearchService` | Singleton | `provide_nfe_search_service` (existing) |
| `BackupService` | Singleton | `provide_backup_service` (existing) |
| `FetchHandler` | Singleton | `provide_fetch_handler` (existing) |
| `SaveHandler` | Singleton | `provide_save_handler` (existing) |
| `ExpenseFetchHandler` | Singleton | `provide_expense_fetch_handler` (existing) |
| `ExpenseSaveHandler` | Singleton | `provide_expense_save_handler` (existing) |
| `_CertificateHandler` | Singleton | `provide_certificate_handler` (existing) |
| `FreightDistributionService` | Singleton | `provide_freight_distribution_service` (existing) |
| `XmlImportService` | Singleton | `provide_xml_import_service` (existing) |
| `ValidationService` | Singleton | `provide_validation_service` (existing) |
| `BusinessService` | Singleton | `provide_business_service` (existing) |
| `ProductBridge` | Singleton | `provide_product_bridge` (existing) |
| `OrderBridge` | Singleton | `provide_order_bridge` (existing) |
| `ExpenseBridge` | Singleton | `provide_expense_bridge` (existing) |
| `NfeBridge` | Singleton | `provide_nfe_bridge` (existing) |
| `CertificateBridge` | Singleton | `provide_certificate_bridge` (existing) |
| `OrderSummaryBridge` | Singleton | `provide_order_summary_bridge` (existing) |

### Factory Protocol Types and Implementations (in `factories.py`, registered in `InjectorModule`)

| Named Factory Type | `__call__` Signature | Implementation Class | DI-Resolved Structural Deps |
|-------------------|---------------------|---------------------|----------------------------|
| `ProductListViewFactory` | `(parent: QWidget) -> ProductListView` | `_ProductListViewFactoryImpl` | `ProductBridge` |
| `OrderEditListViewFactory` | `(parent: QWidget) -> OrderEditListView` | `_OrderEditListViewFactoryImpl` | `OrderBridge`, `OrderSummaryBridge`, `BusinessService`, `NfeBridge`, `OrderEditDialogFactory`, `NfeSearchDialogFactory` |
| `ExpenseListViewFactory` | `(parent: QWidget) -> ExpenseListView` | `_ExpenseListViewFactoryImpl` | `ExpenseBridge`, `ExpenseEditDialogFactory` |
| `CertificateStatusViewFactory` | `(parent: QWidget) -> CertificateStatusView` | `_CertificateStatusViewFactoryImpl` | `CertificateBridge`, `CertificateChangeDialogFactory` |
| `OrderEditDialogFactory` | `(parent: QWidget, order_id: str|None, order: Order|None) -> OrderEditDialog` | `_OrderEditDialogFactoryImpl` | `OrderBridge`, `BusinessService` |
| `ExpenseEditDialogFactory` | `(parent: QWidget, month: str) -> ExpenseEditDialog` | `_ExpenseEditDialogFactoryImpl` | `ExpenseBridge` |
| `CertificateChangeDialogFactory` | `(parent: QWidget) -> CertificateChangeDialog` | `_CertificateChangeDialogFactoryImpl` | `CertificateBridge` |
| `NfeSearchDialogFactory` | `(parent: QWidget) -> NfeSearchDialog` | `_NfeSearchDialogFactoryImpl` | `NfeBridge` |

### Standalone Convenience Functions (in `factories.py`, NOT DI-registered)

| Function | Signature | Notes |
|----------|-----------|-------|
| `make_product_list_view` | `(parent: QWidget) -> ProductListView` | Calls `get_injector()` internally |
| `make_order_edit_list_view` | `(parent: QWidget) -> OrderEditListView` | Calls `get_injector()` internally |
| `make_expense_list_view` | `(parent: QWidget) -> ExpenseListView` | Calls `get_injector()` internally |
| `make_certificate_status_view` | `(parent: QWidget) -> CertificateStatusView` | Calls `get_injector()` internally |
| `make_order_edit_dialog` | `(parent, order_id|None, order|None) -> OrderEditDialog` | Calls `get_injector()` internally |
| `make_expense_edit_dialog` | `(parent, month) -> ExpenseEditDialog` | Calls `get_injector()` internally |
| `make_certificate_change_dialog` | `(parent) -> CertificateChangeDialog` | Calls `get_injector()` internally |
| `make_nfe_search_dialog` | `(parent) -> NfeSearchDialog` | Calls `get_injector()` internally |

### Frontend Class Constructor Signatures (After Changes)

| Class | Constructor Signature |
|-------|----------------------|
| `ProductListView` | `(parent: QWidget, product_bridge: ProductBridge)` |
| `OrderEditListView` | `(parent: QWidget, order_bridge: OrderBridge, order_summary_bridge: OrderSummaryBridge, business_service: BusinessService, nfe_bridge: NfeBridge, order_edit_dialog_factory: OrderEditDialogFactory, nfe_search_dialog_factory: NfeSearchDialogFactory)` |
| `ExpenseListView` | `(parent: QWidget, expense_bridge: ExpenseBridge, expense_edit_dialog_factory: ExpenseEditDialogFactory)` |
| `CertificateStatusView` | `(parent: QWidget, certificate_bridge: CertificateBridge, certificate_change_dialog_factory: CertificateChangeDialogFactory)` |
| `OrderEditDialog` | `(parent: QWidget, order_id: str|None, order: Order|None, order_bridge: OrderBridge, business_service: BusinessService)` |
| `OrderItemsCard` | `(parent: QWidget, business_service: BusinessService)` |
| `ExpenseEditDialog` | `(parent: QWidget, month: str, expense_bridge: ExpenseBridge)` |
| `CertificateChangeDialog` | `(parent: QWidget, certificate_bridge: CertificateBridge)` |
| `NfeSearchDialog` | `(parent: QWidget, nfe_bridge: NfeBridge)` |
| `NfeSearchWorker` | `(nfe_key: str, /, nfe_bridge: NfeBridge)` |
| `MainWindow` | `(parent: QWidget|None, product_list_view_factory: ProductListViewFactory, order_edit_list_view_factory: OrderEditListViewFactory, expense_list_view_factory: ExpenseListViewFactory, certificate_status_view_factory: CertificateStatusViewFactory)` |

**Note:** All `Callable[[...], ...]` types have been replaced with named `Protocol` factory types. This makes the DI contract self-documenting and type-checker friendly.

### Classes NOT Requiring DI Changes

These classes have no bridge/service dependencies and are unaffected:

| Class | File |
|-------|------|
| `NavigationBar` | `src/frontend/components/navbar.py` |
| `MonthFilter` | `src/frontend/components/month_filter.py` |
| `Card` | `src/frontend/components/card.py` |
| `TextField` | `src/frontend/components/text_field.py` |
| `ProductRowWidget` | `src/frontend/views/order_edit/product_row_widget.py` |
| `ExpenseRowWidget` | `src/frontend/views/expense_edit/expense_row_widget.py` |
| `ExpenseItemsCard` | `src/frontend/views/expense_edit/expense_items_card.py` |
| `OrderHeaderCard` | `src/frontend/views/order_edit/order_header_card.py` |

Note: `ExpenseItemsCard` and `OrderHeaderCard` take `parent: QWidget | None = None` — these are pure UI components with no data dependencies. They are **not** changed by this plan.

## Summary of What Gets Removed

### Removed patterns (across all view/dialog files):
1. **`| None = None` fallback parameters** — every dependency parameter becomes required.
2. **`if self._xxx is not None: ... else: fallback_function(...)` branches** — all conditional fallback logic removed.
3. **`assert self._xxx is not None` guards** — no longer needed with required parameters.
4. **Module-level backward-compatible re-export functions in bridge modules** — removed in Step 15.
5. **Direct `get_injector()` calls in `MainWindow`** — replaced with factory injection.
6. **Dead `build_layout()` method in `app.py`** — removed.
7. **Raw `Callable[[...], ...]` type annotations** — replaced with named `Protocol` factory types throughout all constructor signatures, DI registrations, and `main.py` resolution.

### Removed imports (across all view/dialog files):
1. Direct imports of backward-compatible bridge functions (`fetch_products`, `fetch_order_summaries`, `import_xml`, `search_nfe_key`, `fetch_certificate_info`, `save_certificate_from_pfx`, `save_expenses`, `fetch_expenses_for_month`).
2. `from injector_module import get_injector` from `app.py`.
3. Bridge class imports from `app.py` (no longer needed).
4. `from typing import Callable` from `main.py` (no longer needed — named Protocol types replace it).
