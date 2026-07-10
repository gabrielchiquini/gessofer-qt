# Gessofer-Qt — Agent Instructions

## Project Snapshot

Gessofer-Qt is a **PySide6 + QML desktop app** (Python entry point) for purchase-order and expense management for a Brazilian building-materials supplier. The previous version was Tauri 2 (Rust backend + Vue 3 frontend); this repo is the Qt rewrite.

- **Runtime:** Python 3 + PySide6 6.11.1
- **UI:** QML (Qt Quick Controls), loaded via `engine.loadFromModule("App", "Main")`
- **QML module:** `App` — declared in `App/qmldir`; `Constants` is a QML singleton
- **Data:** SQLite (local file); the Rust/Tauri backend docs in `docs/` describe the schema and business rules — they remain the source of truth for data model, API contracts, and business logic
- **Plans:** `plans/` contains implementation plans; they are authoritative for intended behavior

## Run the App

```powershell
.\.venv\Scripts\Activate.ps1
python src/main.py
```

Always activate the `.venv` virtual environment before running any Python commands.

`main.py` is at `src/main.py`. It resolves the QML module path relative to itself (`Path(__file__).parent.parent` → project root) and adds it to `engine.addImportPath()`. **Do not change the working directory** — the QML import path is absolute from `src/`'s parent.

## QML Architecture

```
src/main.py          ← entry point; loads QML module "App" → "Main" (main.qml)
App/
├── qmldir           ← declares module "App", registers Constants singleton
├── Main 1.0 main.qml
├── TopNavbar 1.0 TopNavbar.qml
├── WelcomeScreen 1.0 WelcomeScreen.qml
├── NavigationGroup 1.0 NavigationGroup.qml
├── NavItem 1.0 NavItem.qml
├── WelcomeIcon 1.0 WelcomeIcon.qml
└── Constants 1.0 Constants.qml   (singleton)
```

- All components import the singleton via `import "." 1.0` (QML module system).
- `Constants.qml` holds all colors, dimensions, nav data, and text strings.
- **No Python-side `qmlRegisterSingletonType` is needed** — the `qmldir` + `pragma Singleton` handles it.

## Linting QML

```powershell
.\.venv\Scripts\Activate.ps1
& ".venv\Lib\site-packages\PySide6\qmllint.exe" -I . App\*.qml
```

- Always use `-I .` so qmllint finds `App/qmldir`.
- No `.qmllint.ini` exists yet — if you create one, avoid suppressing `UnqualifiedAccess` unless truly necessary.

## Dependencies

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

All dependency management must be done within the `.venv` virtual environment.

Only PySide6 6.11.1 (and its addons/essentials/shiboken6). No Node.js, no pnpm, no Rust toolchain needed for this repo.

## Docs Reference

The `docs/` directory contains the **Tauri-era** documentation (originally for a Vue/Rust rewrite). **It is still valuable** for:

- **Database schema** → `docs/02-database.md`
- **Business rules** → `docs/11-appendix.md` (Appendix B) and `docs/01-overview.md`
- **Currency convention** → stored as **integer cents**, displayed with Brazilian locale (`R$ 1.234,56`)
- **Navigation structure** → `docs/03-frontend-views.md`, `docs/04-frontend-components.md`
- **Migration mapping** → `docs/10-migration-mapping.md` (Vue → PySide6, Tauri → Python, SeaORM → SQLite)
- **Testing patterns** → `docs/09-testing.md` (E2E test scenarios that inform expected behavior)

When in doubt about business logic or data model, read the docs — they describe the *system*, not the *implementation*.

## Plans


Plans are implementation blueprints. They contain detailed architecture, file-by-file diffs, and verification steps. Reference them before making changes to the areas they cover.

## Type Hints

**Type hints are obligatory for all Python code in this project.** Every function, method, and class must have explicit type annotations on:

- All parameters
- The return type
- Class attributes (including dataclass fields)

This applies to:
- New files created under `src/backend/` and any future Python packages.
- Existing Python files that are modified — annotate any untyped parameters and return types.

**Minimum standard:** Every public function must have full type hints. Private/internal functions should also be typed, but the enforcement is focused on the public API surface.

Examples of compliant code:

```python
def cents_to_display(cents: int) -> str:
    ...

def fetch_orders_for_month(self, month: str, year: int) -> list[Order]:
    ...

class ExpenseRepository:
    def __init__(self, session: Session) -> None:
        ...
```

Non-compliant code (no type hints):

```python
def bad_function(param):  # ❌ No parameter annotation, no return type
    ...
```

Enforcement: When reviewing changes, verify that all new or modified Python functions have type hints on parameters and return types. Missing type hints are a blocking issue — do not merge or approve the change until fixed.

## Gotchas

- **`main.qml` is `App/Main.qml`, not the root-level `main.qml`** — the `qmldir` maps `Main 1.0 main.qml`.
- **Navigation is data-driven** — `Constants.navGroups` drives both `TopNavbar` and sidebar items. Changing nav structure means editing only `Constants.qml`.
- **Portuguese UI strings** — all labels, titles, and hint text are in Brazilian Portuguese. Do not "translate" them.
- **Date format** — displayed as `dd/MM/yyyy`, stored internally as `yyyy-MM-dd`. Month queries use `MM/yyyy`.
- **No auth, no multi-user** — single trusted local user assumption.
