# Lean Blueprint: QML → Widgets Migration (src/widgets/ + src/frontend/)

## Summary

Replace the QML frontend with a plain PySide6 widget frontend. The backend (`src/backend/`) is **completely untouched**. A new app-bridge layer (`src/widgets/`) wraps existing backend services with stateless functions. A new widget frontend (`src/frontend/`) builds the UI using default Qt widgets. The main window shows a `QMenuBar` and a `QTableView` directly — no welcome screen, no stacked widget, no QSS.

**Rule: Zero files in `src/backend/` are modified.**

## Architecture

```
src/
├── backend/                    ← EXISTING, UNCHANGED
│   ├── services/               ← qml_business.py, save_order_service.py, etc.
│   ├── qml/                    ← qml_fetch.py, qml_save.py, qml_transformers.py, etc.
│   ├── models/                 ← dto.py (OrderInput, ExpenseInput, PageResponse)
│   ├── utils/                  ← currency.py, date.py
│   ├── injector_module.py      ← get_injector()
│   └── ...
├── widgets/                    ← NEW: app-bridge layer (data access only)
│   ├── __init__.py             ← Re-exports
│   ├── product.py              ← fetch_products, fetch_orders_for_month
│   ├── order.py                ← save_orders
│   ├── expense.py              ← save_expenses, fetch_expenses_for_month
│   └── (NO business.py)        ← Pure business functions live in frontend/
├── frontend/                   ← NEW: widget frontend
│   ├── __init__.py             ← create_main_window
│   ├── constants.py            ← NAV_GROUPS, dimensions, page size
│   ├── navbar.py               ← NavigationBar(QMenuBar)
│   ├── product_list.py         ← ProductListView(QWidget)
│   ├── business.py             ← distribute_freight, import_xml, validate_*
│   └── app.py                  ← MainWindow(QMainWindow)
└── main.py                     ← MODIFIED: entry point only
```

**Import flow:** `frontend` → `widgets` → `backend.*`

---

## File-by-File Specifications

### `src/widgets/__init__.py`

**Purpose:** Package init — re-exports all app-bridge functions so frontend imports from `widgets` (not submodules).

**Imports:**
```python
from .product import fetch_products, fetch_orders_for_month
from .order import save_orders
from .expense import save_expenses, fetch_expenses_for_month
```

**Re-exports (`__all__`):**
```python
__all__ = [
    "fetch_products", "fetch_orders_for_month",
    "save_orders",
    "save_expenses", "fetch_expenses_for_month",
]
```

**Instructions:**
- One import line per submodule, one `__all__` list
- **Do NOT import from `business`** — that file does not exist in `widgets/`

---

### `src/widgets/product.py`

**Purpose:** Stateless fetch functions for product data. Wraps `FetchHandler` from `backend.qml.qml_fetch`.

**Imports:**
```python
from __future__ import annotations
import logging, traceback
from typing import Any, Callable
from sqlalchemy.orm import Session
from backend.injector_module import get_injector
from backend.models.dto import PageResponse
from backend.qml.qml_fetch import FetchHandler
from backend.qml.qml_transformers import product_page_to_dict, orm_order_to_dict
```

**Functions:**

```python
def fetch_products(
    page: int,
    supplier: str = "",
    product: str = "",
    month: str = "",
) -> dict[str, Any]:
    # Returns: {"items": [...], "page": int, "page_count": int, "total": int, "page_size": int}
    # On error: returns empty-page dict via product_page_to_dict(PageResponse(items=[], ...))
```

```python
def fetch_orders_for_month(month: str) -> list[dict[str, Any]]:
    # Returns: list of order dicts (id, date, supplier, nfeKey, freight, unloading, products)
    # On error: returns []
```

**Module-level helpers:**
```python
_fetch_handler: FetchHandler | None = None
_session_factory: Callable[[], Session] | None = None

def _get_fetch_handler() -> FetchHandler:
    # Lazy-init: get_injector() → injector.get(Callable[[], Session]) → FetchHandler(factory)
    # Returns cached handler after first call
```

**Instructions:**
- Lazy-init `FetchHandler` via `_get_fetch_handler()` at module level
- `fetch_products`: call `handler.fetch_products(page, supplier or None, product or None, month or None)`, transform with `product_page_to_dict()`
- `fetch_orders_for_month`: call `handler.fetch_orders_for_month(month)`, list-comprehend with `orm_order_to_dict(o)`
- Catch all exceptions, log, return empty-page result
- No `@Slot`, no Signals, no QML code

---

### `src/widgets/order.py`

**Purpose:** Stateless save function for orders. Wraps `SaveHandler` from `backend.qml.qml_save`.

**Imports:**
```python
from __future__ import annotations
import logging
from typing import Any
from backend.models.dto import OrderInput
from backend.qml.qml_transformers import dict_to_order_input
from backend.qml.qml_save import SaveHandler
from backend.injector_module import get_injector
from backend.services.save_order_service import SaveOrderService, SaveExpenseService
```

**Functions:**

```python
def save_orders(
    orders: list[dict[str, Any]],
    deleted_order_ids: list[str],
) -> bool:
    # Returns: True on success, False on error
```

**Module-level helpers:**
```python
_save_handler: SaveHandler | None = None

def _get_save_handler() -> SaveHandler:
    # Lazy-init: get_injector() → get(SaveOrderService), get(SaveExpenseService) → SaveHandler(sos, ses)
```

**Instructions:**
- Lazy-init `SaveHandler` via `_get_save_handler()` at module level
- Convert each dict to `OrderInput` via `dict_to_order_input(o)`
- Call `handler.save_orders(final_orders, deleted_order_ids)`
- Return `bool` (True/False)

---

### `src/widgets/expense.py`

**Purpose:** Stateless fetch and save functions for expenses. Wraps `FetchHandler` and `SaveHandler`.

**Imports:**
```python
from __future__ import annotations
import logging
from typing import Any, Callable
from sqlalchemy.orm import Session
from backend.models.dto import ExpenseInput
from backend.qml.qml_transformers import expense_to_dict
from backend.qml.qml_fetch import FetchHandler
from backend.qml.qml_save import SaveHandler
from backend.injector_module import get_injector
from backend.services.save_order_service import SaveExpenseService, SaveOrderService
```

**Functions:**

```python
def fetch_expenses_for_month(month: str) -> list[dict[str, Any]]:
    # Returns: list of expense dicts (id, month, description, value)
    # On error: returns []
```

```python
def save_expenses(
    expenses: list[dict[str, Any]],
    month: str,
) -> bool:
    # Returns: True on success, False on error
```

**Module-level helpers:**
```python
_fetch_handler: FetchHandler | None = None
_save_handler: SaveHandler | None = None

def _get_fetch_handler() -> FetchHandler:
    # Lazy-init same pattern as product.py
def _get_save_handler() -> SaveHandler:
    # Lazy-init same pattern as order.py
```

**Instructions:**
- Fetch: `handler.fetch_expenses_for_month(month)` → `[expense_to_dict(e) for e in raw]`
- Save: create `ExpenseInput(description=..., value=...)` for each dict → `handler.save_expenses(inputs, month)`
- Both return list or bool respectively, catching exceptions

---

### `src/widgets/business.py` — DOES NOT EXIST

**Instruction:** This file is **not created**. Pure business functions (`distribute_freight`, `import_xml`, `validate_order`, `validate_expense`) live in `src/frontend/business.py` instead. The `widgets/` layer handles **only data access** (fetch/save).

---

### `src/frontend/__init__.py`

**Purpose:** Package init — exposes `create_main_window` for `main.py`.

```python
from __future__ import annotations
from .app import MainWindow
__all__ = ["MainWindow"]
```

**Instructions:**
- Re-export `MainWindow` (not `create_main_window` — the class is instantiated directly)
- One import, one `__all__`

---

### `src/frontend/constants.py`

**Purpose:** Python constants mirroring `Constants.qml` — navigation data, dimensions, page size. **No colors, no QSS, no welcome text.**

**Constants:**
```python
NAV_GROUPS: list[dict[str, Any]] = [
    {"title": "Notas", "items": [
        {"label": "Pedidos", "group": "Notas"},
        {"label": "Cadastrar", "group": "Notas"},
    ]},
    {"title": "Despesas", "items": [
        {"label": "Lista", "group": "Despesas"},
        {"label": "Cadastrar", "group": "Despesas"},
    ]},
]

SIDEBAR_WIDTH: int = 200
SIDEBAR_HEADER_HEIGHT: int = 56
NAV_ITEM_HEIGHT: int = 40
CONTENT_MARGINS: int = 40
MIN_WINDOW_WIDTH: int = 800
MIN_WINDOW_HEIGHT: int = 600
PRODUCT_PAGE_SIZE: int = 50
```

**Instructions:**
- `NAV_GROUPS` drives `NavigationBar` menu construction
- Dimensions used for sizing widgets
- `PRODUCT_PAGE_SIZE` used by `ProductListView` for pagination

---

### `src/frontend/navbar.py`

**Purpose:** A `QMenuBar` with dropdown menus driven by `NAV_GROUPS`. Emits `item_clicked` signal on activation.

**Imports:**
```python
from __future__ import annotations
from PySide6.QtWidgets import QMenuBar, QMenu, QAction
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from frontend.constants import NAV_GROUPS
```

**Class:**
```python
class NavigationBar(QMenuBar):
    item_clicked: Signal(str, str)  # (label, group_title)

    def __init__(self, parent: QWidget | None = None) -> None:
        # super().__init__(parent)
        # setObjectName("navbar")
        # _build_menus()
```

**Widget tree:**
```
NavigationBar (QMenuBar)
├── QMenu "Notas"                   → objectName: "nav-menu-notas"
│   ├── QAction "Pedidos"           → objectName: "nav-link-pedidos"
│   └── QAction "Cadastrar"         → objectName: "nav-link-cadastrar"
└── QMenu "Despesas"                → objectName: "nav-menu-despesas"
    ├── QAction "Lista"             → objectName: "nav-link-lista"
    └── QAction "Cadastrar"         → objectName: "nav-link-cadastrar"
```

**Methods:**
```python
def _build_menus(self) -> None:
    # Iterate NAV_GROUPS → QMenu(title) → QAction(label) per item
    # Connect each QAction.triggered → lambda → self.item_clicked.emit(lbl, grp)
    # Use closure capture (lbl=label, grp=grp) to avoid late-binding bug
    # self.addMenu(menu)
```

**Instructions:**
- No styling, no setStyleSheet
- ObjectNames match QML equivalents for consistency
- Signal carries `(label, group_title)` for MainWindow navigation routing

---

### `src/frontend/product_list.py`

**Purpose:** Filter form + QTableView with pagination. The primary data view.

**Imports:**
```python
from __future__ import annotations
import logging
from typing import Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QTableView,
    QScrollArea, QHeaderView,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
from backend.utils.currency import cents_to_display
from backend.utils.date import iso_to_br_date
from frontend.constants import PRODUCT_PAGE_SIZE
```

**Class:**
```python
class ProductListView(QWidget):
    _current_page: int
    _page_count: int
    _total: int

    def __init__(self, parent: QWidget | None = None) -> None:
        # super().__init__(parent)
        # _current_page = 1, _page_count = 1, _total = 0
        # _setup_ui()
        # _connect_signals()
        # clear_filters()   ← auto-load on init
```

**Widget tree:**
```
ProductListView (QWidget)
└── QVBoxLayout (spacing=5, margins=10)
    ├── QFrame (filter form, StyledPanel)
    │   └── QHBoxLayout (spacing=8)
    │       ├── QLabel "Fornecedor"
    │       ├── QLineEdit filter_supplier (placeholder: "Fornecedor")
    │       ├── QLabel "Produto"
    │       ├── QLineEdit filter_product (placeholder: "Produto")
    │       ├── QLabel "Mês"
    │       ├── QLineEdit filter_month (inputMask="99/9999", fixedWidth=100, placeholder: "MM/AAAA")
    │       ├── QPushButton "Consultar" (btn_search)
    │       └── QPushButton "Limpar" (btn_clear)
    ├── QScrollArea (stretch=1)
    │   └── QTableView table_view
    │       ├── setEditTriggers(NoEditTriggers)
    │       ├── setSelectionBehavior(SelectRows)
    │       ├── setAlternatingRowColors(True)
    │       └── QStandardItemModel (6 columns)
    └── QHBoxLayout (pagination, spacing=8)
        ├── QPushButton "◀" (btn_prev)
        ├── QLabel page_label ("Página 1 de 1")
        └── QPushButton "▶" (btn_next)
```

**Model columns (QStandardItemModel):**
| Col | Header | Data source | Formatting |
|-----|--------|-------------|------------|
| 0 | Data | `item["date"]` | `iso_to_br_date()` |
| 1 | Fornecedor | `item["supplier"]` | raw string |
| 2 | Produto | `item["name"]` | raw string |
| 3 | Preço | `item["price"]` (cents) | `cents_to_display()` |
| 4 | Total | `item["totalPrice"]` (cents) | `cents_to_display()` |
| 5 | Pedido | `item["orderId"]` | raw string |

**Methods:**
```python
def search(self) -> None:
    # _current_page = 1; _refresh_page()

def clear_filters(self) -> None:
    # filter_supplier.clear(), filter_product.clear(), filter_month.clear()
    # _current_page = 1; _refresh_page()

def go_previous(self) -> None:
    # if _current_page > 1: _current_page -= 1; _refresh_page()

def go_next(self) -> None:
    # if _current_page < _page_count: _current_page += 1; _refresh_page()

def update_pagination(self) -> None:
    # page_label.text = f"Página {_current_page} de {_page_count}"
    # btn_prev.setEnabled(_current_page > 1)
    # btn_next.setEnabled(_current_page < _page_count)

def _refresh_page(self) -> None:
    # from widgets.product import fetch_products
    # Read filter text, call fetch_products(page, supplier, product, month)
    # Catch exceptions, _process_result(result)

def _process_result(self, result: dict[str, Any]) -> None:
    # _total = result["total"], _page_count = result["page_count"]
    # _model.setRowCount(0)
    # For each item: appendRow([QStandardItem(...) for each column])
    # update_pagination()

def _setup_ui(self) -> None:
    # Build widget tree above

def _setup_model(self) -> None:
    # QStandardItemModel(0, 6)
    # setHorizontalHeaderLabels(["Data", "Fornecedor", "Produto", "Preço", "Total", "Pedido"])
    # Set column resize modes: 0=ResizeToContents, 1=Stretch, 2=Stretch, 3=ResizeToContents, 4=ResizeToContents, 5=ResizeToContents
    # table_view.setModel(_model)

def _connect_signals(self) -> None:
    # btn_search.clicked → search
    # btn_clear.clicked → clear_filters
    # btn_prev.clicked → go_previous
    # btn_next.clicked → go_next
```

**Instructions:**
- Call `clear_filters()` in `__init__` to auto-load page 1 on startup
- `_refresh_page` does a **local import** of `fetch_products` from `widgets.product` (avoids circular dependency at module level)
- Currency formatted with `cents_to_display()` from `backend.utils.currency`
- Dates formatted with `iso_to_br_date()` from `backend.utils.date`
- No styling — default Qt only
- `setAlternatingRowColors(True)` is the only visual enhancement

---

### `src/frontend/business.py`

**Purpose:** Pure business functions — freight distribution, XML import, validation. **No state, no Signals, no UI.**

**Imports:**
```python
from __future__ import annotations
import logging
from typing import Any
from backend.qml.qml_transformers import (
    dict_to_order_input,
    freight_result_to_dict,
    xml_import_result_to_dict,
)
from backend.qml.qml_business import BusinessHandler
from backend.injector_module import get_injector
from backend.services.freight_distribution import FreightDistributionService
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportService
```

**Functions:**

```python
def distribute_freight(order: dict[str, Any]) -> dict[str, Any]:
    # order_input = dict_to_order_input(order)
    # result = handler.distribute_freight(order_input)
    # return freight_result_to_dict(result)
    # On ValueError: return {}
```

```python
def import_xml(file_path: str) -> dict[str, Any]:
    # result = handler.import_xml(file_path)
    # return xml_import_result_to_dict(result)
    # On error: return {"orders": [], "warnings": []}
```

```python
def validate_order(order: dict[str, Any]) -> dict[str, Any]:
    # order_input = dict_to_order_input(order)
    # result = handler.validate_order(order_input)
    # return {"valid": result.valid, "errors": result.errors}
    # On error: return {"valid": False, "errors": [str(exc)]}
```

```python
def validate_expense(description: str, value: int) -> dict[str, Any]:
    # result = handler.validate_expense(description, value)
    # return {"valid": result.valid, "errors": result.errors}
    # On error: return {"valid": False, "errors": [str(exc)]}
```

**Module-level helper:**
```python
_business_handler: BusinessHandler | None = None

def _get_business_handler() -> BusinessHandler:
    # Lazy-init: ValidationService(), FreightDistributionService(), XmlImportService()
    # → BusinessHandler(validation, freight, xml_import)
```

**Instructions:**
- All four functions are **pure** — no instance state, no Signals
- Each creates/uses a module-level `BusinessHandler` singleton
- Uses transformers from `backend.qml.qml_transformers` for result conversion
- Handle errors gracefully (return empty/error dicts, don't raise)
- **This file is in `frontend/`, NOT in `widgets/`** — the `widgets` layer is data access only

---

### `src/frontend/app.py`

**Purpose:** Main application window — `QMainWindow` with `QMenuBar` and `ProductListView`.

**Imports:**
```python
from __future__ import annotations
from PySide6.QtWidgets import QMainWindow
from frontend.constants import MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from frontend.navbar import NavigationBar
from frontend.product_list import ProductListView
```

**Class:**
```python
class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        # super().__init__(parent)
        # setWindowTitle("Gessofer")
        # setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        # _build_ui()

    def _build_ui(self) -> None:
        # self.nav_bar = NavigationBar(self)
        # self.setMenuBar(self.nav_bar)
        # self.product_list = ProductListView(self)
        # self.setCentralWidget(self.product_list)
        # self.nav_bar.item_clicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, label: str, group_title: str) -> None:
        # if label == "Pedidos" and group_title == "Notas":
        #     self.product_list.search()
        # # Other nav items: ignored for now (product list stays visible)
```

**Widget tree:**
```
MainWindow (QMainWindow)
├── QMenuBar ← NavigationBar
│   ├── QMenu "Notas"
│   │   ├── QAction "Pedidos"
│   │   └── QAction "Cadastrar"
│   └── QMenu "Despesas"
│       ├── QAction "Lista"
│       └── QAction "Cadastrar"
└── centralWidget ← ProductListView
```

**Instructions:**
- No welcome screen, no QStackedWidget — `ProductListView` is always the central widget
- "Pedidos" click → `product_list.search()` refreshes data
- Other nav items acknowledged but not implemented yet
- No styling, no setStyleSheet

---

### `src/main.py` — MODIFIED

**Current state:** QML entry point — `QQmlApplicationEngine`, `BackendManager`, QML module path setup.

**Changes:**
- Remove all QML imports (`QQmlApplicationEngine`, `qmlRegisterType`)
- Remove `BackendManager` import
- Remove QML path resolution (`qml_path`, `app_dir`)
- Remove `engine.addImportPath()`, `engine.rootContext().setContextProperty()`
- Remove `engine.loadFromModule()`
- Import `QApplication` from `PySide6.QtWidgets` (already present)
- Import `MainWindow` from `frontend.app`
- Create `QApplication`, set org/app name
- Add `src/` to `sys.path` (already present)
- Instantiate `MainWindow()`, show, exec
- Remove `os` import (unused)

**New structure:**
```python
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from frontend.app import MainWindow

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Gessofer")
    app.setOrganizationName("Gessofer")
    src_dir = Path(__file__).resolve().parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

**Instructions:**
- No `setStyleSheet()`
- No bridge instantiation
- Minimal entry point only
- `sys.path` manipulation unchanged (adds `src/`)

---

## Implementation Order

| Step | File | Dependencies | Notes |
|------|------|-------------|-------|
| 1 | `src/widgets/__init__.py` | None | Package init only |
| 2 | `src/widgets/product.py` | `backend.qml.*`, `backend.injector_module` | Foundation — most-used fetch |
| 3 | `src/widgets/order.py` | `backend.qml.*`, `backend.services.*` | Save function |
| 4 | `src/widgets/expense.py` | `backend.qml.*`, `backend.services.*` | Fetch + save |
| 5 | `src/frontend/constants.py` | None | Foundation for all frontend |
| 6 | `src/frontend/navbar.py` | `frontend.constants` | Simple widget, no backend deps |
| 7 | `src/frontend/product_list.py` | `frontend.constants`, `widgets.product`, `backend.utils.*` | Most complex widget |
| 8 | `src/frontend/app.py` | `frontend.constants`, `frontend.navbar`, `frontend.product_list` | Assembles UI |
| 9 | `src/frontend/__init__.py` | `frontend.app` | Package init |
| 10 | `src/main.py` | `frontend` | Final integration |

**Note:** `src/frontend/business.py` can be written at any time — it is not used by the current single-view MVP but should be created before the "Cadastrar" views are added.

---

## Verification Steps

1. **Run the app:** `.\.venv\Scripts\Activate.ps1 && python src/main.py`
   - Window opens with title "Gessofer", min size 800x600
   - Default Qt appearance (no custom colors/QSS)

2. **Verify menu bar:** "Notas" and "Despesas" menus present with correct items
   - Click "Pedidos" → product list refreshes

3. **Verify product list auto-loads:** On startup, table shows page 1 of products
   - Filter form shows "Fornecedor", "Produto", "Mês" fields
   - "Mês" has input mask "99/9999"

4. **Verify filtering:** "Consultar" with supplier/product/month filters returns matching results
   - "Limpar" clears all fields and reloads page 1

5. **Verify formatting:** Currency as "R$ 1.234,56", dates as "dd/MM/yyyy"

6. **Verify pagination:** "Página X de Y" label, prev/next buttons enable/disable correctly

7. **Verify coexistence:** Reverting `main.py` to original QML content still works (QML files untouched)

---

## Risks

- **Thread safety:** SQLite `StaticPool` with `check_same_thread=False` is safe for single-threaded desktop. All widget callbacks run on the main thread.
- **QStandardItemModel performance:** With `PAGE_SIZE=50` this is fine. If pagination grows, consider `QAbstractTableModel`.
- **Import path resolution:** `sys.path.insert(0, str(src_dir))` in `main.py` makes `backend`, `widgets`, and `frontend` all resolvable as top-level packages.
- **Module-level lazy init:** Simple singleton pattern for `FetchHandler`/`SaveHandler`/`BusinessHandler`. Thread-safe for single-threaded use only.
- **Empty nav items:** "Cadastrar" (Notas), "Lista" and "Cadastrar" (Despesas) do nothing yet — product list stays visible. Future work.
- **Default Qt styling:** May look different from the QML version. Intentional per scope. Can be added later via QSS.
- **Type hints:** All Python code must have full type hints on parameters and return types (project convention).

---

## Explicit: No Existing Files Modified

- **Zero files in `src/backend/` are modified** — services, qml, models, utils, repositories, entities, database, `injector_module.py`, `errors.py` — all untouched.
- **Zero QML files are modified or deleted** — `App/Main.qml`, `Constants.qml`, etc. remain as-is.
- **Only file modified:** `src/main.py` (replaced QML entry point with widget entry point).
- **New directories created:** `src/widgets/` and `src/frontend/` with the files specified above.
