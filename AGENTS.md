# Gessofer-Qt — Agent Instructions

## Project Snapshot

Gessofer-Qt is a **PySide6 desktop app** (pure QtWidgets, **no QML**) for purchase-order and expense management for **Gessofer**, a Brazilian building-materials supplier (gypsum/plaster products). Rewrite from Tauri 2.

- **Runtime:** Python 3 + PySide6 6.11.1 (+ Addons, Essentials, shiboken6)
- **Run:** `.\.venv\Scripts\Activate.ps1 && python src/main.py` — never change working directory; `main.py` adds `src/` to `sys.path`
- **Install:** `.\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt`
- **Dependencies:** PySide6 6.11.1, Addons, Essentials, SQLAlchemy 2.0.51, injector 0.24.0, pytest 9.1.1, pytest-qt 4.5.0, cryptography 49.0.0, lxml 6.1.1, requests 2.34.2, signxml 5.1.0, QT-PyQt-PySide-Custom-Widgets 2.2.1. No Node.js, no Rust.

## Structure

```
src/
├── main.py                          ← entry point (adds src/ to sys.path)
├── di/injector_module.py            ← DI composition root
├── frontend/
│   ├── app.py                       ← MainWindow
│   ├── constants.py                 ← NAV_GROUPS drives menu bar
│   ├── navbar.py                    ← NavigationBar (QMenuBar)
│   ├── components/                  ← Card, MonthFilter, TextField, NavBar
│   ├── factories/                   ← 8 DI-injected view/dialog factories
│   ├── views/                       ← order_edit/, expense_edit/, certificate_status/
│   ├── util/                        ← icons, validators
│   └── workers/                     ← NfeSearchWorker (QThread)
├── bridge/                          ← DTO ↔ ORM API surface (6 modules)
├── models/                          ← dataclass DTOs (no __init__.py)
│   ├── input.py                     ← OrderInput, ExpenseInput, ProductInput
│   ├── output.py                    ← ExpenseOutput, Product, PageResponse
│   ├── order.py                     ← Order, OrderSummary, FreightResult, XmlImportResult
│   ├── certificate.py               ← CertificateInfo
│   └── validation.py                ← Validation
└── backend/                         ← namespace package (no __init__.py)
    ├── business.py                  ← BusinessService orchestrator
    ├── entities/orm.py              ← SQLAlchemy ORM: Order, Product, Expense
    ├── repositories/                ← order_repository.py, expense_repository.py
    ├── services/                    ← 9 service modules
    ├── certificate/                 ← PFX import, PEM parsing
    ├── sefaz/                       ← SEFAZ NFe consultation
    ├── database/connection.py       ← SQLite engine + path discovery
    ├── errors.py                    ← BackendError hierarchy
    └── utils/                       ← currency, date, text, backup
```

## Key Architecture

- No QML. Pure PySide6.QtWidgets.
- `NAV_GROUPS` in `src/frontend/constants.py` drives the menu bar.
- Bridge layer converts dataclass DTOs ↔ ORM entities.
- DI via `injector` — `get_injector()` in `src/di/injector_module.py`. Singletons.
- Session-per-operation: each bridge call creates fresh Session, uses it, closes it.
- Factory pattern: view/dialog classes via factory protocols in DI.
- `src/backend/` is a namespace package (PEP 420). Direct submodule paths only.
- **no `__init__.py`** — imports to avoid circular imports.
- NFe SEFAZ search runs in a `QThread` via `NfeSearchWorker`.

## Database

- Schema source of truth: `docs/02-database.md` (3 tables: ORDER, PRODUCT, EXPENSE)
- Discovery: (1) `DATABASE_URL` env → (2) CWD `main.db` → (3) `%LOCALAPPDATA%\gessofer-tauri\main.db` → (4) error
- Test DB: in-memory SQLite via `temp_engine` fixture in `tests/fixtures/database.py`
- Backup dir: `%LOCALAPPDATA%\gessofer-app\backups\`
- Certificate storage: `%LOCALAPPDATA%\gessofer-app\certificate\`
- NFe receipts: `%LOCALAPPDATA%\gessofer-app\notas\`
- `main.db*` is gitignored.

## Tests

- `.\.venv\Scripts\Activate.ps1 && pytest` — no config files, uses defaults.
- Root `conftest.py` adds `src/` to `sys.path`.
- Fixtures: `tests/fixtures/database.py` (temp_engine, session_factory, fetch_handler), `tests/fixtures/orders.py` (seeded_fetch_handler, sample_page), `tests/fixtures/expenses.py` (expense_list_widget)
- Test files: `test_backup_service.py`, `test_certificate_bridge.py`, `test_certificate_import.py`, `test_certificate_read_pem.py`, `test_expense_list.py`
- Utilities: `tests/util/bridge_reset.py` — resets bridge singletons and DI state
- Test DB isolation: each test gets temp-engine with temp-file SQLite. Seeds orders + expenses, patches DI, resets singletons.
- `pytest-qt` used for widget tests.

## Conventions

- **Date:** display `dd/MM/yyyy`, stored `yyyy-MM-dd` (ISO). Month filter: `MM/yyyy` for orders, `YYYY-MM` for expenses.
- **Currency:** integer cents. Displayed via `cents_to_display()` → `"250,00"`.
- **Text:** `normalize_text()` strips accents, lowercases, ASCII-only — fuzzy search.
- **Type hints:** obligatory for ALL Python code. Missing hints = blocking.
- **Portuguese UI:** labels, titles, hint text in Brazilian Portuguese. Do not translate to English.
- **Code/thinking/agent output:** English.

## Gotchas

- `main.py` is at `src/main.py`, not root.
- `NAV_GROUPS` in `src/frontend/constants.py` drives the menu bar.
- DI container is module-level singleton — `_get_app_injector()` lazy-creates.
- `save_orders` uses "delete-then-insert" pattern in one transaction.
- Freight/unloading distribution only updates unit PRICE; TOTAL per product unchanged.
- XML import parses NFe XML, adding IPI and ICMS-ST to base price.
- `discover_database_path()` in `connection.py` has intentional print() debug aids.
- `product_list.py` uses `floordiv` from `operator` for column width — intentional.
- `_on_item_clicked` in `app.py` handles nav routing via central widget replacement.
- No CI, no pre-commit, no linting config.
- `deploy.ps1` at root runs: `pyside6-deploy.exe -c .\src\pysidedeploy.spec .\src\main.py`
- `docs/` has Tauri-era docs but they are source of truth for schema/business rules.
- `plans/` directory contains implementation plans (markdown).
- `ctx.md` at root is a redundant copy of context-mode routing rules — can be deleted.

## Implementation Order

1. Backend — entities (if schema changes), repositories, services, DTOs in `models/`
2. Bridge — new API functions DTOs ↔ ORM
3. Frontend — UI widgets consuming the bridge
4. Update `NAV_GROUPS` in `src/frontend/constants.py` if adding nav
5. Add DI bindings in `src/di/injector_module.py`
6. Update test seed data if new entities
7. Update docs if business rules change

## Docs Reference

| File | Purpose |
|------|---------|
| `docs/01-overview.md` | Business context, glossary (NFe, frete, descarga) |
| `docs/02-database.md` | Schema, relationships, migration |
| `docs/03-frontend-views.md` | View descriptions |
| `docs/04-frontend-components.md` | Component specs |
| `docs/05-utilities.md` | Date/currency/XML utilities |
| `docs/06-backend.md` | Tauri backend (reference only) |
| `docs/07-styling.md` | UI styling, FluentUI3 theme |
| `docs/08-build-deployment.md` | PySide6 deployment |
| `docs/09-testing.md` | E2E test scenarios |
| `docs/10-migration-mapping.md` | Vue→PySide6, Tauri→Python |
| `docs/11-appendix.md` | Business rules, file index |
| `docs/README.md` | TOC |
