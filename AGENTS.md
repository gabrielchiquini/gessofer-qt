# Gessofer-Qt — Agent Instructions

## Project Snapshot

Gessofer-Qt is a **PySide6 desktop app** (pure Python widgets, **no QML**) for purchase-order and expense management for **Gessofer**, a Brazilian building-materials supplier (gypsum/plaster products). The previous version was Tauri 2 (Rust backend + Vue 3 frontend); this repo is the Qt rewrite.

- **Runtime:** Python 3 + PySide6 6.11.1 (plus Addons, Essentials, shiboken6)
- **UI:** Pure PySide6 widgets (`QMainWindow` + `QMenuBar` + `QTableView` + filter forms)
- **Data:** SQLite (`main.db`); schema in `docs/02-database.md`
- **DI:** `injector` library — composition root in `src/di/injector_module.py`
- **Currency:** stored as **integer cents**, displayed with Brazilian locale (`R$ 1.234,56`)
- **Deployment:** PySide6 Deploy (`pyside6-deploy.exe`), config in `src/pysidedeploy.spec`

## Run the App

```powershell
.\.venv\Scripts\Activate.ps1
python src/main.py
```

Always activate `.venv` first. **Do not change the working directory** — `main.py` adds `src/` to `sys.path` so `import frontend.*`, `import backend.*`, `import bridge.*`, `import models.*` all resolve.

## Install Dependencies

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Dependencies:** `PySide6 6.11.1`, `PySide6_Addons`, `PySide6_Essentials`, `SQLAlchemy 2.0.51`, `injector 0.24.0`, `pytest 9.1.1`, `pytest-qt 4.5.0`, `cryptography 49.0.0`, `lxml 6.1.1`, `requests 2.34.2`, `signxml 5.1.0`, `QT-PyQt-PySide-Custom-Widgets 2.2.1`. No Node.js, no Rust.

## Architecture

```
src/
├── main.py                          ← entry point
├── di/
│   └── injector_module.py           ← DI composition root
├── frontend/
│   ├── app.py                       ← MainWindow
│   ├── constants.py                 ← NAV_GROUPS, dimensions
│   ├── navbar.py                    ← NavigationBar (QMenuBar)
│   ├── components/                  ← reusable UI components (Card, MonthFilter, TextField)
│   ├── factories/                   ← factory protocols for DI-injected views/dialogs
│   ├── views/                       ← view specific classes 
│   ├── util/                        ← icons, validators
│   └── workers/                     ← NfeSearchWorker (QThread)
├── bridge/                          ← API surface: DTOs ↔ ORM
├── models/                          ← dataclass DTOs (input, output, order, validation, certificate)
├── backend/                         ← layered backend (namespace package, no __init__.py)
│   ├── business.py                  ← BusinessService orchestrator
│   ├── entities/orm.py              ← SQLAlchemy ORM: Order, Product, Expense
│   ├── repositories/                ← raw SQL queries
│   ├── services/                    ← business logic + handlers
│   ├── certificate/                 ← PFX import, PEM parsing
│   ├── sefaz/                       ← SEFAZ NFe consultation
│   ├── database/connection.py       ← SQLite engine setup
│   ├── errors.py                    ← BackendError hierarchy
│   └── utils/                       ← currency, date, text, backup
```

**Key architectural facts:**
- **No QML.** The UI is pure `PySide6.QtWidgets`.
- **Navigation is data-driven** — `NAV_GROUPS` in `src/frontend/constants.py` drives the menu bar. Editing that dict changes the nav.
- **Bridge layer** converts between dataclass DTOs (used by widgets) and ORM entities. The bridge is the public API surface.
- **DI via `injector`** — `get_injector()` in `src/di/injector_module.py` creates the composition root. All services, bridges, and view factories are registered as singletons.
- **Session-per-operation** — each bridge call creates a fresh Session, uses it, and closes it.
- **Factory pattern** — view and dialog classes are instantiated via factory protocols registered in the DI container. `main.py` resolves factories from the injector and passes them to `MainWindow`.
- **`conftest.py`** (root-level) adds `src/` to `sys.path` so `backend` imports work in tests.
- **`src/backend/` is a namespace package** — all `__init__.py` files have been removed (PEP 420). Imports use direct submodule paths.
- **`src/models/` is a regular package** — its `__init__.py` is preserved and re-exports DTOs.
- **Background workers** — NFe SEFAZ search runs in a `QThread` via `NfeSearchWorker` to keep the UI responsive.

## Database

- **Schema source of truth:** `docs/02-database.md` (3 tables: `ORDER`, `PRODUCT`, `EXPENSE`)
- **DB discovery priority:** (1) `DATABASE_URL` env var → (2) CWD `main.db` → (3) `%LOCALAPPDATA%\gessofer-tauri\main.db` → (4) error
- **Production path:** `%LOCALAPPDATA%\gessofer-tauri\main.db`
- **Test DB:** in-memory SQLite via `temp_engine` fixture in `tests/fixtures/database.py`
- **Backup dir:** `%LOCALAPPDATA%\gessofer-app\backups\` (daily backups, tiered retention: 10 days daily, 20 days weekly, monthly archive)
- **Certificate storage:** `%LOCALAPPDATA%\gessofer-app\certificate\` (PEM + private key)
- **NFe receipts:** `%LOCALAPPDATA%\gessofer-app\notas\` (saved XML files)
- **main.db** is in `.gitignore` — if you see one in the repo root it's local data, not committed.

## Running Tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest
```

- No `pytest.ini`, no `setup.cfg`, no `pyproject.toml` test config — uses defaults.
- Fixtures live in `tests/fixtures/` (re-exported via root `tests/conftest.py`):
  - `tests/fixtures/database.py`: `temp_engine`, `session_factory`, `fetch_handler`
  - `tests/fixtures/orders.py`: `seeded_fetch_handler` (plain function), `sample_page`
  - `tests/fixtures/expenses.py`: `expense_list_widget`
- **Test files:** `tests/test_backup_service.py`, `tests/test_certificate_bridge.py`, `tests/test_certificate_import.py`, `tests/test_certificate_read_pem.py`, `tests/test_expense_list.py`
- **Test utilities:** `tests/util/bridge_reset.py` — resets bridge singletons and DI state between tests
- **Test DB isolation:** Each test gets its own `temp_engine` instance with a temp-file SQLite DB. `temp_engine` seeds both orders and expenses, patches the DI container, and resets bridge singletons.
- **pytest-qt** is used for widget-based tests.

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

All labels, titles, and hint text are in Brazilian Portuguese. Do not "translate" them to English. Besides that, all code, thinking and agent output must be in English.

## Gotchas

- **`main.py` is at `src/main.py`**, not the project root.
- **No QML, no qmldir, no QML module system.** The UI is pure `PySide6.QtWidgets`.
- **`NAV_GROUPS` in `src/frontend/constants.py` drives the menu bar.** Changing nav = editing that dict.
- **DI container is a module-level singleton** — `_get_app_injector()` in `src/di/injector_module.py` lazily creates the `Injector` on first call.
- **`save_orders` uses a "delete-then-insert" pattern** — old orders (by ID) are deleted, then new ones inserted, all in one transaction.
- **Freight/unloading distribution** only updates the unit `PRICE`; the `TOTAL` per product remains unchanged.
- **XML import** parses NFe (Nota Fiscal Eletrônica) XML, adding IPI and ICMS-ST to base price per docs §3.2.5.
- **`main.db*` is gitignored** — the `main.db` in the repo root is local data.
- **`docs/` contains Tauri-era docs** but they are the **source of truth** for schema, business rules, and expected behavior. Read them when in doubt.
- **`src/backend/` is a namespace package** — no `__init__.py` files. All imports use direct submodule paths (e.g., `from backend.entities.orm import Order`, not `from backend import Order`).
- **`src/models/` is a regular package** — its `__init__.py` is preserved. DTOs are imported from `models.*` (e.g., `from models.input import OrderInput`).
- **No CI, no pre-commit, no linting config** — the project currently has no automated quality gates beyond type hints.
- **`_on_item_clicked` in `app.py`** handles nav routing by replacing the central widget. New nav items need a corresponding entry in `NAV_GROUPS` and a handler in `_on_item_clicked`.
- **`print()` statements in `connection.py`** — the `discover_database_path()` function prints which DB path is being used ("Using DATABASE_URL DB", "Using CWD DB", "Using PROD DB"). These are intentional debug aids.
- **`product_list.py` uses `floordiv` from `operator`** for column width calculation — this is intentional for integer division.

## Docs Reference

| File | Purpose |
|------|---------|
| `docs/01-overview.md` | Business context, glossary (NFe, frete, descarga, etc.), currency format |
| `docs/02-database.md` | Schema, relationships, migration from legacy, field naming conventions |
| `docs/03-frontend-views.md` | View descriptions (Tauri-era, but logic applies) |
| `docs/04-frontend-components.md` | Component specs |
| `docs/05-utilities.md` | Date/currency/XML utilities |
| `docs/06-backend.md` | Tauri backend (reference only) |
| `docs/07-styling.md` | UI styling, FluentUI3 theme |
| `docs/08-build-deployment.md` | PySide6 deployment, build config |
| `docs/09-testing.md` | E2E test scenarios |
| `docs/10-migration-mapping.md` | Vue→PySide6, Tauri→Python, SeaORM→SQLite |
| `docs/11-appendix.md` | Business rules (Appendix B), complete file index |
| `docs/README.md` | Documentation table of contents |

## Implementation Order (when adding features)

1. **Backend first** — entities (if schema changes), repositories, services, DTOs in `models/`
2. **Bridge layer** — new API functions converting DTOs ↔ ORM
3. **Frontend widgets** — UI components consuming the bridge
4. **Update `NAV_GROUPS`** in `src/frontend/constants.py` if adding navigation items
5. **Add DI bindings** in `src/di/injector_module.py` for new factories/services
6. **Update `tests/conftest.py`** seed data if new entities exist
7. **Update docs** if business rules change

## context-mode MCP Tools — Quick Reference

context-mode MCP tools are available for all agent interactions. These rules protect the context window from flooding — one unrouted command can dump 56 KB into context.

### Think in Code

Analyze/count/filter/compare/search/parse/transform data: **write code** via `ctx_execute(language, code)`, `console.log()` only the answer. Do NOT read raw data into context. PROGRAM the analysis, not COMPUTE it. Pure JavaScript — Node.js built-ins only (`fs`, `path`, `child_process`). `try/catch`, handle `null`/`undefined`. One script replaces ten tool calls.

### Tool Selection Priority

| Priority | Tool | When to Use |
|----------|------|-------------|
| 0 | `ctx_search(sort: "timeline")` | On resume: check prior decisions, errors, plans BEFORE asking the user |
| 1 | `ctx_batch_execute(commands, queries)` | Run 3+ related commands in parallel. Auto-indexes output, returns search results in one call. Each command: `{label: "header", command: "..."}` |
| 2 | `ctx_search(queries: ["q1", "q2"])` | Follow-up queries against indexed content. Batch ALL questions in one array |
| 3 | `ctx_execute(language, code)` | Sandbox execution for data processing. Only stdout enters context |
| 3 | `ctx_execute_file(path, language, code)` | File-level analysis. FILE_CONTENT variable holds raw bytes in sandbox |
| 4 | `ctx_fetch_and_index(url, source)` | Web fetching — raw HTML never enters context. Use `concurrency: N` for multi-URL |
| 5 | `ctx_index(content, source)` | Store content in FTS5 for later search via `ctx_search` |
| 6 | `ctx_stats` | Display context consumption statistics |
| 7 | `ctx_doctor` | Diagnose context-mode installation |
| 8 | `ctx_upgrade` | Upgrade context-mode to latest version |
| 9 | `ctx_purge(confirm: true)` | Destructive: wipe knowledge base or session. Requires confirmation |

### Blocked Operations

- **curl/wget** — intercepted and blocked. Use `ctx_fetch_and_index` or `ctx_execute` with `fetch()`
- **Inline HTTP** — `fetch('http`, `requests.get(`, `requests.post(` intercepted. Use `ctx_execute`
- **Direct web fetching** — use `ctx_fetch_and_index(url, source)` then `ctx_search(queries)`

### Redirected Operations

- **Shell (>20 lines output)** — Use `ctx_batch_execute` or `ctx_execute` instead of Bash. Bash only for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`
- **File reading (for analysis)** — Reading to **edit** → reading is correct. Reading to **analyze/explore/summarize** → `ctx_execute_file(path, language, code)`
- **grep (large results)** — Use `ctx_execute` in sandbox for portable filtering/counting

### Concurrency

For `ctx_batch_execute` and `ctx_fetch_and_index`, **always include `concurrency: N`** (1-8):
- Use **4-8** for I/O-bound work (network calls, API queries, multi-repo git reads)
- Keep at **1** for CPU-bound (npm test, build, lint) or shared-state commands (ports, lock files)
- GitHub API rate-limit: cap at 4 for `gh` calls

### Memory — Search Before Asking

Session history is persistent and searchable. On resume, search BEFORE asking the user:

| Need | Command |
|------|---------|
| What did we decide? | `ctx_search(queries: ["decision"], source: "decision", sort: "timeline")` |
| What constraints exist? | `ctx_search(queries: ["constraint"], source: "constraint")` |
| What errors occurred? | `ctx_search(queries: ["error", "failure"])` |
| What was the plan? | `ctx_search(queries: ["plan", "approach"])` |

**Common session-memory source labels:** `decision`, `error`, `error-resolution`, `blocker`, `plan`, `user-prompt`, `rejected-approach`, `compaction`

**DO NOT ask "what were we working on?" — SEARCH FIRST.** If search returns 0 results, proceed as a fresh session.

### Session Continuity

Skills, roles, and decisions persist for the entire session. Do not abandon them as the conversation grows. After `/clear` or `/compact`: knowledge base and session stats are preserved. Use `ctx purge` to start fresh.

### Writing Artifacts

Write artifacts (code, configs, plans, docs) to FILES — never inline. Return: file path + 1-line description. Use descriptive source labels for `ctx_search(source: "label")`.
