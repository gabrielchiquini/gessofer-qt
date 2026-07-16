# Gessofer-Qt — Agent Instructions

## Project Snapshot

Gessofer-Qt is a **PySide6 desktop app** (pure Python widgets, **no QML**) for purchase-order and expense management for a Brazilian building-materials supplier. The previous version was Tauri 2 (Rust backend + Vue 3 frontend); this repo is the Qt rewrite.

- **Runtime:** Python 3 + PySide6 6.11.1 (plus Addons, Essentials, shiboken6)
- **UI:** Pure PySide6 widgets (`QMainWindow` + `QMenuBar` + `QTableView` + filter forms)
- **Data:** SQLite (`main.db`); schema in `docs/02-database.md`
- **DI:** `injector` library — composition root in `src/backend/injector_module.py`
- **Currency:** stored as **integer cents**, displayed with Brazilian locale (`R$ 1.234,56`)

## Run the App

```powershell
.\.venv\Scripts\Activate.ps1
python src/main.py
```

Always activate `.venv` first. **Do not change the working directory** — `main.py` adds `src/` to `sys.path` so `import frontend.*` etc. resolve.

## Install Dependencies

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Only PySide6 (6.11.1) + SQLAlchemy 2.0.51 + injector 0.22.0 + pytest 9.1.1. No Node.js, no Rust.

## Architecture

```
src/main.py                          ← entry point; creates QApplication + MainWindow
src/frontend/app.py                  ← MainWindow (QMainWindow) with menu bar + central widget
src/frontend/navbar.py               ← NavigationBar (QMenuBar) driven by NAV_GROUPS data
src/frontend/product_list.py         ← ProductListView (QWidget): filter form + QTableView + pagination
src/frontend/constants.py            ← NAV_GROUPS data, dimensions, PAGE_SIZE
src/frontend/business.py             ← business bridge: freight distribution, XML import, validation
src/bridge/                          ← API surface for frontend; converts dicts ↔ ORM entities
src/bridge/product.py                ← fetch_products(), fetch_orders_for_month(), lazy FetchHandler
src/bridge/order.py                  ← save_orders(), lazy SaveHandler
src/bridge/expense.py                ← save_expenses(), fetch_expenses_for_month()
src/bridge/__init__.py               ← TypedDict definitions (ProductDict, OrderDict, etc.)
src/backend/                         ← layered backend
src/backend/entities/orm.py          ← SQLAlchemy ORM: Order, Product, Expense
src/backend/repositories/            ← OrderRepository, ExpenseRepository (raw SQL queries)
src/backend/services/                ← SaveOrderService, SaveExpenseService, XmlImportService,
                                         ValidationService, FreightDistributionService
src/backend/models/dto.py            ← dataclass DTOs (OrderInput, ProductInput, ExpenseInput, PageResponse)
src/backend/database/connection.py   ← SQLite engine with StaticPool, WAL mode, FK enforcement
src/backend/injector_module.py       ← DI container (injector library): Engine, Session factory, Services
src/backend/errors.py                ← BackendError hierarchy (ValidationError, DatabaseError, XmlParseError)
src/backend/utils/                   ← currency.py, date.py, text.py
```

**Key architectural facts:**
- **No QML.** The existing AGENTS.md described a QML architecture that does not exist. This is a pure PySide6 widget app.
- **Navigation is data-driven** — `NAV_GROUPS` in `src/frontend/constants.py` drives the menu bar. Editing that dict changes the nav.
- **Bridge layer** converts between dict-based API contracts (used by widgets) and ORM entities / DTOs. The bridge is the public API surface.
- **DI via `injector`** — `get_injector()` creates the composition root. Bridge modules lazily initialize handlers via the injector.
- **Session-per-operation** — each bridge call creates a fresh Session, uses it, and closes it.
- **`conftest.py`** (root-level) adds `src/` to `sys.path` so `backend` imports work in tests.

## Database

- **Schema source of truth:** `docs/02-database.md` (3 tables: `ORDER`, `PRODUCT`, `EXPENSE`)
- **DB discovery priority:** (1) `DATABASE_URL` env var → (2) CWD `main.db` → (3) `%LOCALAPPDATA%\gessofer-tauri\main.db` → (4) error
- **Production path:** `%LOCALAPPDATA%\gessofer-tauri\main.db`
- **Test DB:** in-memory SQLite via `in_memory_engine` fixture in `tests/conftest.py`
- **main.db** is in `.gitignore` — if you see one in the repo root it's local data, not committed.

## Running Tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest
```

- No `pytest.ini`, no `setup.cfg`, no `pyproject.toml` test config — uses defaults.
- Fixtures live in `tests/conftest.py`: `in_memory_engine`, `session_factory`, `seeded_fetch_handler`, `fetch_handler`, `sample_page`.
- **No test files exist yet** (no `test_*.py`). The conftest seeds 5 orders with 6 products for integration-style tests.
- The conftest documents a known bug: the `supplier` filter in `search_products` filters on `Product.NAME_NORMALIZED` instead of `Order.SUPPLIER_NORMALIZED`. Tests should reflect this actual behavior.

## Date & Currency Conventions

- **Display date:** `dd/MM/yyyy` (e.g., `10/07/2024`)
- **Stored date:** `yyyy-MM-dd` (ISO)
- **Month filter:** `MM/yyyy` for orders, `YYYY-MM` for expenses
- **Currency:** stored as **integer cents** (e.g., `25000` = R$250,00). Displayed via `cents_to_display()` → `"250,00"`.
- **Normalized text:** `normalize_text()` strips accents, lowercases, ASCII-only — used for fuzzy search on supplier and product names.

## Type Hints

**Type hints are obligatory for all Python code.** Every function, method, and class must have:
- All parameter annotations
- Return type annotation
- Class attributes (including dataclass fields)

**Minimum:** every public function must be fully typed. Private/internal functions should also be typed.

Compliant:
```python
def cents_to_display(cents: int) -> str: ...
def fetch_orders_for_month(self, month: str, year: int) -> list[Order]: ...
```

Non-compliant:
```python
def bad_function(param): ...  # ❌
```

Missing type hints are a blocking issue.

## Portuguese UI Strings

All labels, titles, and hint text are in Brazilian Portuguese. Do not "translate" them to English.

## Gotchas

- **`main.py` is at `src/main.py`**, not the project root.
- **No QML, no qmldir, no QML module system.** The UI is pure `PySide6.QtWidgets`.
- **`NAV_GROUPS` in `src/frontend/constants.py` drives the menu bar.** Changing nav = editing that dict.
- **Bridge modules use lazy singletons** (`_fetch_handler`, `_save_handler`) initialized via `get_injector()`.
- **`save_orders` uses a "delete-then-insert" pattern** — old orders (by ID) are deleted, then new ones inserted, all in one transaction.
- **Freight/unloading distribution** only updates the unit `PRICE`; the `TOTAL` per product remains unchanged.
- **XML import** parses NFe (Nota Fiscal Eletrônica) XML, adding IPI and ICMS-ST to base price per docs §3.2.5.
- **`main.db*` is gitignored** — the `main.db` in the repo root is local data.
- **`docs/` contains Tauri-era docs** but they are the **source of truth** for schema, business rules, and expected behavior. Read them when in doubt.
- **`plans/` is empty** — no implementation plans exist yet.
- **No CI, no pre-commit, no linting config** — the project currently has no automated quality gates beyond type hints.
- **`_get_app_injector()` is a module-level singleton** — calling `get_injector()` multiple times returns the same instance after the first call.
- **`order_repository.py` has a `print(month)` debug statement** on line 82 — remove before committing changes.
- **`app.py` has a dead `build_layout()` method** (lines 40-44) that is never called.

## Docs Reference

| File | Purpose |
|------|---------|
| `docs/01-overview.md` | Business context, glossary |
| `docs/02-database.md` | Schema, relationships, migration |
| `docs/03-frontend-views.md` | View descriptions (Tauri-era, but logic applies) |
| `docs/04-frontend-components.md` | Component specs |
| `docs/05-utilities.md` | Date/currency/XML utilities |
| `docs/06-backend.md` | Tauri backend (reference only) |
| `docs/10-migration-mapping.md` | Vue→PySide6, Tauri→Python, SeaORM→SQLite |
| `docs/11-appendix.md` | Business rules (Appendix B) |
| `docs/09-testing.md` | E2E test scenarios |

## Implementation Order (when adding features)

1. **Backend first** — entities (if schema changes), repositories, services, DTOs
2. **Bridge layer** — new API functions converting dicts ↔ ORM
3. **Frontend widgets** — UI components consuming the bridge
4. **Update `NAV_GROUPS`** if adding navigation items
5. **Update `tests/conftest.py`** seed data if new entities exist
6. **Update docs** if business rules change
