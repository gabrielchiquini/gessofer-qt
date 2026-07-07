# Implementation Plan: Python Backend Data Layer for Gessofer-Qt (SQLAlchemy Edition)

## Summary

This plan details the creation of the Python backend data layer for the Gessofer-Qt desktop application. The backend provides database access, ORM entity definitions, repository functions, data-transfer objects, and utility functions. The backend will use **SQLAlchemy 2.0.51** as the ORM with the modern 2.0 style (`Mapped`, `mapped_column`, `select()`, `Session`), and operates against an **externally-managed SQLite database** (tables are assumed to already exist — no DDL creation). The scope covers only the database/ORM/repositories/utils layer: no business-logic services, no API/command layer, and no custom exception hierarchy.

---

## 1. Directory Structure

```
gessofer-qt/
├── src/
│   ├── main.py                          # Entry point (existing)
│   ├── backend/                         # NEW: backend package
│   │   ├── __init__.py                  # Package init; exports public API
│   │   ├── database/
│   │   │   ├── __init__.py              # Package init
│   │   │   └── connection.py            # DB discovery, SQLAlchemy engine/session
│   │   ├── entities/
│   │   │   ├── __init__.py              # Package init
│   │   │   └── orm.py                   # SQLAlchemy declarative models (Order, Product, Expense)
│   │   ├── models/
│   │   │   ├── __init__.py              # Package init
│   │   │   └── dto.py                   # Plain dataclass DTOs (OrderInput, ProductInput, ExpenseInput, PageResponse)
│   │   ├── repositories/
│   │   │   ├── __init__.py              # Package init
│   │   │   ├── order_repository.py      # Order + Product SQLAlchemy queries
│   │   │   └── expense_repository.py    # Expense SQLAlchemy queries
│   │   └── utils/
│   │       ├── __init__.py              # Package init
│   │       ├── currency.py              # Cents ↔ display string
│   │       ├── date.py                  # Date format conversions
│   │       └── text.py                  # ASCII normalization
│   └── requirements.txt                 # Add SQLAlchemy==2.0.51
└── requirements.txt                     # Add SQLAlchemy==2.0.51
```

**Rationale for structure:**
- `src/backend/` mirrors the Rust `src-tauri/src/` module layout (database → entities → models → repositories → utils).
- `entities/` contains SQLAlchemy declarative models that map to DB tables.
- `models/` contains plain dataclass DTOs — these are **not ORM entities**, they are UI-facing data transfer objects for input and serialization.
- `repositories/` handles all SQLAlchemy queries using the `Session` pattern.
- `utils/` is shared infrastructure (currency, date, text normalization).
- **Removed:** `services/` (business logic), `api/` (command layer), `errors.py` (exception hierarchy), `schema.sql` (DDL), `init_database()` (schema creation).

---

## 2. File-by-File Plan

### 2.1 `src/backend/database/__init__.py`

**Purpose:** Package init — exports `discover_database_path` and `get_engine`.

```python
from .connection import discover_database_path, get_engine

__all__ = ["discover_database_path", "get_engine"]
```

---

### 2.2 `src/backend/database/connection.py` — Database Connection Management

**Purpose:** Database file discovery and SQLAlchemy engine creation. No schema initialization.

**Constants:**
```python
DEFAULT_DB_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "gessofer-tauri")
DEFAULT_DB_FILE = "main.db"
TEST_DB_PREFIX = "tmp-gessofer-tauri"
```

**Functions:**

```python
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import Engine


def discover_database_path() -> str:
    """
    Discover the database file path using the priority order:
    1. DATABASE_URL environment variable (development/tests)
    2. %LOCALAPPDATA%\\gessofer-tauri\\main.db (production)
    3. %TEMP%\\tmp-gessofer-tauri.db (tests fallback)

    Returns the absolute path as a string.
    Raises FileNotFoundError if no database is found and no env var is set.
    """
    # Step 1: Check DATABASE_URL
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Strip "sqlite://" prefix if present
        path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        return os.path.abspath(path)

    # Step 2: Check production path
    prod_path = os.path.join(DEFAULT_DB_DIR, DEFAULT_DB_FILE)
    if os.path.isfile(prod_path):
        return os.path.abspath(prod_path)

    # Step 3: Check test path
    temp_dir = os.environ.get("TEMP", os.environ.get("TMP", ""))
    if temp_dir:
        test_path = os.path.join(temp_dir, f"{TEST_DB_PREFIX}.db")
        if os.path.isfile(test_path):
            return os.path.abspath(test_path)

    raise FileNotFoundError(
        "Nenhum arquivo de banco encontrado. "
        "Defina DATABASE_URL ou coloque main.db em %LOCALAPPDATA%\\gessofer-tauri\\"
    )


def get_engine(db_path: str | None = None) -> Engine:
    """
    Return a SQLAlchemy Engine configured for SQLite.

    Uses StaticPool with check_same_thread=False for desktop-app thread safety.
    WAL mode and foreign keys are enabled via connect_args PRAGMA settings.

    If db_path is None, calls discover_database_path().

    The database schema (tables) is assumed to already exist externally.
    This function does NOT create or initialize the schema.
    """
    if db_path is None:
        db_path = discover_database_path()

    engine = create_engine(
        f"sqlite:///{db_path}",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Enable WAL mode and foreign keys on each new connection
    from sqlalchemy.event import register

    @register(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
```

**Key details:**
- `discover_database_path()` exactly mirrors the Rust logic from `docs/02-database.md` §2.5.
- `get_engine()` returns a SQLAlchemy `Engine` — callers create `Session` instances from it as needed.
- `StaticPool` is used because this is a desktop app with a single connection (no connection pooling needed).
- `check_same_thread=False` is required for SQLite with SQLAlchemy's StaticPool.
- WAL mode and foreign keys are enabled via the `connect` event listener (runs on every new connection).
- **No `init_database()` function** — the database schema is assumed to already exist. Tables are created externally (e.g., via the Tauri-era migration or manual SQL execution).

---

### 2.3 `src/backend/entities/__init__.py`

**Purpose:** Package init — exports all SQLAlchemy ORM entities.

```python
from .orm import Order, Product, Expense

__all__ = ["Order", "Product", "Expense"]
```

---

### 2.4 `src/backend/entities/orm.py` — SQLAlchemy Declarative Models

**Purpose:** Define all SQLAlchemy ORM entities that map to DB tables. Uses the SQLAlchemy 2.0 style (`Mapped`, `mapped_column`).

**Imports:**
```python
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
```

**Base class:**
```python
class Base(DeclarativeBase):
    pass
```

**Entity: Order**
```python
class Order(Base):
    __tablename__ = "ORDER"

    ID: Mapped[str] = mapped_column("ID", String, primary_key)
    DATE: Mapped[date] = mapped_column("DATE", Date)
    SUPPLIER: Mapped[str] = mapped_column("SUPPLIER", String)
    SUPPLIER_NORMALIZED: Mapped[str] = mapped_column("SUPPLIER_NORMALIZED", String)
    NFE_KEY: Mapped[Optional[str]] = mapped_column("NFE_KEY", String, nullable=True)
    FREIGHT: Mapped[int] = mapped_column("FREIGHT", Integer)
    UNLOADING: Mapped[int] = mapped_column("UNLOADING", Integer)
    CREATED_AT: Mapped[datetime] = mapped_column("CREATED_AT", DateTime)
    UPDATED_AT: Mapped[datetime] = mapped_column("UPDATED_AT", DateTime)

    # Relationship to Product (backref on Product)
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="order", cascade="all, delete-orphan"
    )
```

**Entity: Product**
```python
class Product(Base):
    __tablename__ = "PRODUCT"

    ID: Mapped[str] = mapped_column("ID", String, primary_key)
    NAME: Mapped[str] = mapped_column("NAME", String)
    NAME_NORMALIZED: Mapped[str] = mapped_column("NAME_NORMALIZED", String)
    QUANTITY: Mapped[int] = mapped_column("QUANTITY", Integer)
    PRICE: Mapped[int] = mapped_column("PRICE", Integer)
    TOTAL_PRICE: Mapped[int] = mapped_column("TOTAL_PRICE", Integer)
    ORDER_ID: Mapped[str] = mapped_column("ORDER_ID", ForeignKey("ORDER.ID"))
    ITEM_ORDINAL: Mapped[Optional[int]] = mapped_column("ITEM_ORDINAL", Integer, nullable=True)
    CREATED_AT: Mapped[datetime] = mapped_column("CREATED_AT", DateTime)
    UPDATED_AT: Mapped[datetime] = mapped_column("UPDATED_AT", DateTime)

    # Back-reference to Order
    order: Mapped["Order"] = relationship("Order", back_populates="products")
```

**Entity: Expense**
```python
class Expense(Base):
    __tablename__ = "EXPENSE"

    ID: Mapped[int] = mapped_column("ID", Integer, primary_key, autoincrement=True)
    MONTH: Mapped[str] = mapped_column("MONTH", String)
    DESCRIPTION: Mapped[str] = mapped_column("DESCRIPTION", String)
    VALUE: Mapped[int] = mapped_column("VALUE", Integer)
    CREATED_AT: Mapped[datetime] = mapped_column("CREATED_AT", DateTime)
    UPDATED_AT: Mapped[datetime] = mapped_column("UPDATED_AT", DateTime)
```

**Key details:**
- All column names use the **exact DB column names** as defined in the original schema (e.g., `ID`, `DATE`, `SUPPLIER`, `NFE_KEY`).
- `Order` uses `String` for `ID` (UUID string), `Date` for `DATE`, `DateTime` for timestamps.
- `Product` uses `ForeignKey("ORDER.ID")` — note the quoted table name `"ORDER"` in the actual DB.
- `Expense` uses `Integer` with `autoincrement=True` for its primary key (matching `AUTOINCREMENT` in the DDL).
- `products` relationship on `Order` has `cascade="all, delete-orphan"` so deleting an Order cascades to its Products.
- `NFE_KEY` is nullable (`nullable=True`).
- `ITEM_ORDINAL` is nullable (`nullable=True`).
- Timestamps use Python `datetime` objects — SQLAlchemy handles the SQLite `DATETIME` storage.

---

### 2.5 `src/backend/models/__init__.py`

**Purpose:** Package init — exports all DTO dataclasses.

```python
from .dto import OrderInput, ProductInput, ExpenseInput, PageResponse

__all__ = ["OrderInput", "ProductInput", "ExpenseInput", "PageResponse"]
```

---

### 2.6 `src/backend/models/dto.py` — Data Transfer Object Dataclasses

**Purpose:** Plain dataclasses for UI-facing input/output. These are **not ORM entities** — they carry no SQLAlchemy decorators, no table mappings, and no relationships. They are used by the repository layer to accept input from the UI and to return structured results.

**Imports:**
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar, List, Optional
```

**T and TypeVar for pagination:**
```python
T = TypeVar("T")
```

**DTO: OrderInput (input from UI)**
```python
@dataclass
class OrderInput:
    """Data sent from the UI to save orders."""
    id: str
    date: str                      # YYYY-MM-DD
    supplier: str
    nfe_key: str = ""              # empty string → NULL in DB
    freight: int = 0               # cents
    unloading: int = 0             # cents
    products: List[ProductInput] = field(default_factory=list)
```

**DTO: ProductInput (input from UI)**
```python
@dataclass
class ProductInput:
    """Data sent from the UI for a single product line."""
    id: str
    name: str
    quantity: int
    price: int                     # unit price in cents
    total: int                     # total_price in cents
    order_id: str
    item_ordinal: Optional[int] = None
```

**DTO: ExpenseInput (input from UI)**
```python
@dataclass
class ExpenseInput:
    """Data sent from the UI to save an expense."""
    description: str
    value: int                     # cents
    # ID is not sent from UI — auto-generated by DB
```

**DTO: PageResponse (generic pagination)**
```python
@dataclass
class PageResponse(Generic[T]):
    """Paginated response matching the Tauri PageResponse."""
    items: List[T]
    page: int
    page_count: int
    total: int                     # total number of matching rows
    page_size: int
```

**Key details:**
- These are **plain dataclasses**, completely decoupled from SQLAlchemy.
- They serve as the contract between the UI layer and the repository layer.
- `nfe_key` defaults to `""` (empty string means NULL in the DB — repository code handles this conversion).
- Monetary fields are `int` (cents) — never `float`.

---

### 2.7 `src/backend/repositories/__init__.py`

**Purpose:** Package init — exports repository classes.

```python
from .order_repository import OrderRepository
from .expense_repository import ExpenseRepository

__all__ = ["OrderRepository", "ExpenseRepository"]
```

---

### 2.8 `src/backend/repositories/order_repository.py` — Order + Product Repository

**Purpose:** All SQLAlchemy queries for ORDER and PRODUCT tables using the `Session` pattern.

**Imports:**
```python
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, Sequence

from sqlalchemy import select, delete, insert, update
from sqlalchemy.orm import Session

from backend.entities.orm import Order, Product
from backend.models.dto import OrderInput, ProductInput, PageResponse
from backend.utils.text import normalize_text
```

**Constants:**
```python
PAGE_SIZE: int = 50
```

**Class: OrderRepository**
```python
class OrderRepository:
    """Repository for ORDER and PRODUCT tables using SQLAlchemy 2.0."""

    def __init__(self, session: Session):
        self.session = session

    # ── Query: fetch_orders_for_month ───────────────────────────────

    def fetch_orders_for_month(self, month: str, year: int) -> List[Order]:
        """
        Fetch all orders and their products for a given year-month.
        month = "07" (zero-padded), year = 2024.
        Returns list of Order ORM entities with products eagerly loaded.
        """
        date_start = f"{year:04d}-{month:02d}-01"
        if month == "12":
            next_month = "01"
            next_year = year + 1
        else:
            next_month = str(int(month) + 1).zfill(2)
            next_year = year
        date_end = f"{next_year:04d}-{next_month:02d}-01"

        stmt = (
            select(Order)
            .where(Order.DATE >= date_start, Order.DATE < date_end)
            .order_by(Order.DATE.desc(), Order.ID.asc())
        )
        orders = self.session.execute(stmt).scalars().all()

        # Products are loaded via the relationship (lazy by default)
        # Accessing order.products triggers the lazy load.
        return orders

    # ── Query: search_products (paginated search) ───────────────────

    def search_products(
        self,
        page: int,
        supplier: Optional[str] = None,
        product: Optional[str] = None,
        month: Optional[str] = None,
    ) -> PageResponse[Product]:
        """
        Paginated product search with optional filters.
        page is 1-based.
        month format: "MM/yyyy" (e.g., "07/2024").

        Returns PageResponse with matching Product ORM entities.
        """
        where_clauses = []
        params = {}

        # Filter by supplier (normalized LIKE)
        if supplier:
            normalized_supplier = normalize_text(supplier)
            where_clauses.append(Product.NAME_NORMALIZED.like(f"%{normalized_supplier}%"))
            params["supplier"] = f"%{normalized_supplier}%"

        # Filter by product name (normalized LIKE)
        if product:
            normalized_product = normalize_text(product)
            where_clauses.append(Product.NAME_NORMALIZED.like(f"%{normalized_product}%"))
            params["product"] = f"%{normalized_product}%"

        # Filter by month (MM/yyyy) — joins through ORDER table
        if month:
            try:
                m_str, y_str = month.split("/")
                m = int(m_str)
                y = int(y_str)
            except (ValueError, IndexError):
                raise ValueError(f"Formato de mês inválido: '{month}'")

            date_start = f"{y:04d}-{m:02d}-01"
            if m == 12:
                next_m = "01"
                next_y = y + 1
            else:
                next_m = str(m + 1).zfill(2)
                next_y = y
            date_end = f"{next_y:04d}-{next_m:02d}-01"

            subquery = (
                select(Order.ID)
                .where(Order.DATE >= date_start, Order.DATE < date_end)
                .scalar_subquery()
            )
            where_clauses.append(Product.ORDER_ID.in_(subquery))

        where_sql = ""
        if where_clauses:
            where_sql = " AND ".join(
                clause.compile(compile_kwargs={"literal_binds": True})
                for clause in where_clauses
            )
            # For simplicity in this plan, use parameterized approach:
            # Actual implementation uses session.execute with a combined select

        # Total count (for pagination)
        count_stmt = select(Product.ID).where(*where_clauses)  # type: ignore[arg-type]
        total = self.session.execute(count_stmt).scalars().count()

        # Page count
        page_count = (total + PAGE_SIZE - 1) // PAGE_SIZE if total > 0 else 0

        # Fetch page
        offset = (page - 1) * PAGE_SIZE
        query_stmt = (
            select(Product)
            .where(*where_clauses)  # type: ignore[arg-type]
            .order_by(Product.NAME.asc())
            .limit(PAGE_SIZE)
            .offset(offset)
        )
        products = self.session.execute(query_stmt).scalars().all()

        return PageResponse(
            items=list(products),
            page=page,
            page_count=page_count,
            total=total,
            page_size=PAGE_SIZE,
        )

    # ── Write: delete_orders ────────────────────────────────────────

    def delete_orders(self, order_ids: Sequence[str]) -> None:
        """Delete orders by their UUIDs. Called inside a transaction."""
        if not order_ids:
            return
        stmt = delete(Order).where(Order.ID.in_(order_ids))  # type: ignore[arg-type]
        self.session.execute(stmt)

    # ── Write: insert_order ─────────────────────────────────────────

    def insert_order(self, order: OrderInput) -> None:
        """Insert a single order row. Timestamps are auto-generated by DB."""
        nfe_key_val = order.nfe_key if order.nfe_key else None
        now = datetime.now()
        order_entity = Order(
            ID=order.id,
            DATE=order.date,
            SUPPLIER=order.supplier,
            SUPPLIER_NORMALIZED=normalize_text(order.supplier),
            NFE_KEY=nfe_key_val,
            FREIGHT=order.freight,
            UNLOADING=order.unloading,
            CREATED_AT=now,
            UPDATED_AT=now,
        )
        self.session.add(order_entity)

    # ── Write: delete_order_products ────────────────────────────────

    def delete_order_products(self, order_ids: Sequence[str]) -> None:
        """Delete all products belonging to given order IDs."""
        if not order_ids:
            return
        stmt = delete(Product).where(Product.ORDER_ID.in_(order_ids))  # type: ignore[arg-type]
        self.session.execute(stmt)

    # ── Write: insert_product ───────────────────────────────────────

    def insert_product(self, product: ProductInput) -> None:
        """Insert a single product row. Timestamps are auto-generated by DB."""
        now = datetime.now()
        product_entity = Product(
            ID=product.id,
            NAME=product.name,
            NAME_NORMALIZED=normalize_text(product.name),
            QUANTITY=product.quantity,
            PRICE=product.price,
            TOTAL_PRICE=product.total,
            ORDER_ID=product.order_id,
            ITEM_ORDINAL=product.item_ordinal,
            CREATED_AT=now,
            UPDATED_AT=now,
        )
        self.session.add(product_entity)
```

**Key details:**
- All queries use `Session.execute(select(...))` — the SQLAlchemy 2.0 style.
- `fetch_orders_for_month` uses `select(Order)` with `.where()` and `.order_by()`.
- `search_products` builds dynamic WHERE clauses using SQLAlchemy core constructs.
- Delete operations use `delete(Model).where(...)` pattern.
- Insert operations create entity instances and call `session.add()`.
- `nfe_key` conversion from empty string to `None` happens in `insert_order`.
- `normalize_text()` is called for `SUPPLIER_NORMALIZED` and `NAME_NORMALIZED` fields.

---

### 2.9 `src/backend/repositories/expense_repository.py` — Expense Repository

**Purpose:** All SQLAlchemy queries for the EXPENSE table.

**Imports:**
```python
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from backend.entities.orm import Expense
from backend.models.dto import ExpenseInput
```

**Class: ExpenseRepository**
```python
class ExpenseRepository:
    """Repository for the EXPENSE table using SQLAlchemy 2.0."""

    def __init__(self, session: Session):
        self.session = session

    def fetch_expenses_for_month(self, month: str) -> List[Expense]:
        """
        Fetch all expenses for a given YYYY-MM month.
        month format: "YYYY-MM" (e.g., "2024-07").
        """
        stmt = (
            select(Expense)
            .where(Expense.MONTH == month)
            .order_by(Expense.ID.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def delete_expenses_for_month(self, month: str) -> None:
        """Delete all expenses for a given month. Called inside a transaction."""
        stmt = delete(Expense).where(Expense.MONTH == month)
        self.session.execute(stmt)

    def insert_expense(self, expense: ExpenseInput, month: str) -> None:
        """Insert a single expense row. ID and timestamps are auto-generated by DB."""
        now = datetime.now()
        expense_entity = Expense(
            MONTH=month,
            DESCRIPTION=expense.description,
            VALUE=expense.value,
            CREATED_AT=now,
            UPDATED_AT=now,
        )
        self.session.add(expense_entity)
```

**Key details:**
- `insert_expense` does NOT set `ID` — the DB auto-generates it via `AUTOINCREMENT`.
- `month` is passed as a separate parameter because the `ExpenseInput` DTO does not contain a month field.
- All queries use `select(Expense).where(...)` pattern.

---

### 2.10 `src/backend/utils/__init__.py`

**Purpose:** Package init.

```python
from .currency import cents_to_display, parse_currency_to_cents
from .date import parse_month_for_orders, br_date_to_iso, iso_to_br_date
from .text import normalize_text

__all__ = [
    "cents_to_display",
    "parse_currency_to_cents",
    "parse_month_for_orders",
    "br_date_to_iso",
    "iso_to_br_date",
    "normalize_text",
]
```

---

### 2.11 `src/backend/utils/currency.py` — Currency Utilities

**Purpose:** Convert between integer cents and Brazilian locale display strings.

**Functions:**

```python
def cents_to_display(cents: int) -> str:
    """
    Convert integer cents to Brazilian currency display string.
    Example: 123456 → "1.234,56"
    Example: -123456 → "-1.234,56"
    Example: 0 → "0,00"
    Example: 99 → "0,99"
    """
    if cents < 0:
        sign = "-"
        abs_cents = -cents
    else:
        sign = ""
        abs_cents = cents

    # Integer part: group by thousands with "." separator
    integer_part = abs_cents // 100
    decimal_part = abs_cents % 100

    # Format integer part with dots as thousand separators
    int_str = f"{integer_part:03d}"  # ensure at least 3 digits
    formatted = ""
    while len(int_str) > 3:
        formatted = "." + int_str[-3:] + formatted
        int_str = int_str[:-3]
    formatted = int_str + formatted

    return f"{sign}{formatted},{decimal_part:02d}"


def parse_currency_to_cents(value: str) -> int:
    """
    Parse a Brazilian currency display string to integer cents.
    Handles both "." as thousand separator and "," as decimal separator.
    Also handles raw numbers without separators.

    Examples:
        "1.234,56" → 123456
        "1234.56"  → 123456 (if comma is used as thousand sep)
        "123456"   → 123456 (raw number, treated as cents)
        "0,99"     → 99
        "0,00"     → 0
        ""          → 0 (empty string → zero)

    Returns 0 for empty or unparseable input.
    """
    if not value or not value.strip():
        return 0

    s = value.strip()

    # Determine separators
    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        # Determine which is the decimal separator
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        if last_comma > last_dot:
            # Brazilian format: "1.234,56"
            s = s.replace(".", "").replace(",", ".")
        else:
            # European format: "1,234.56"
            s = s.replace(",", "").replace(".", ",")
    elif has_comma:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_dot:
        parts = s.rsplit(".", 1)
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")
        else:
            pass

    try:
        result = round(float(s) * 100)
        return result
    except ValueError:
        return 0
```

**Key details:**
- Both functions are pure (no side effects).
- `cents_to_display()` uses the Brazilian convention: dots for thousands, comma for decimal.
- `parse_currency_to_cents()` handles multiple input formats to be robust against different UI input patterns.

---

### 2.12 `src/backend/utils/date.py` — Date Utilities

**Purpose:** Convert between BR format (`dd/MM/yyyy`) and ISO format (`yyyy-MM-dd`), and parse month strings.

```python
from datetime import datetime

BR_DATE_FORMAT = "%d/%m/%Y"
ISO_DATE_FORMAT = "%Y-%m-%d"
MONTH_ORDER_FORMAT = "%m/%Y"        # MM/yyyy for orders
MONTH_EXPENSE_FORMAT = "%Y-%m"      # YYYY-MM for expenses


def br_date_to_iso(br_date: str) -> str:
    """
    Convert BR format 'dd/MM/yyyy' to ISO 'yyyy-MM-dd'.
    Returns empty string if parsing fails.
    """
    try:
        return datetime.strptime(br_date, BR_DATE_FORMAT).strftime(ISO_DATE_FORMAT)
    except ValueError:
        return ""


def iso_to_br_date(iso_date: str) -> str:
    """
    Convert ISO 'yyyy-MM-dd' to BR 'dd/MM/yyyy'.
    Returns empty string if parsing fails.
    """
    try:
        return datetime.strptime(iso_date, ISO_DATE_FORMAT).strftime(BR_DATE_FORMAT)
    except ValueError:
        return ""


def parse_month_for_orders(month: str) -> tuple[int, int]:
    """
    Parse month string in 'MM/yyyy' format to (month, year) tuple.
    Example: "07/2024" → (7, 2024)

    Returns (month: int, year: int).

    Raises ValueError for invalid format.
    """
    parts = month.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"Formato de mês inválido: '{month}'. Esperado 'MM/yyyy'.")

    m = int(parts[0])
    y = int(parts[1])

    if not (1 <= m <= 12):
        raise ValueError(f"Mês inválido: {m}. Deve estar entre 1 e 12.")
    if y < 1900 or y > 2100:
        raise ValueError(f"Ano inválido: {y}. Deve estar entre 1900 e 2100.")

    return m, y


def parse_month_for_expenses(month: str) -> str:
    """
    Validate and return month string in 'YYYY-MM' format.
    Example: "2024-07" → "2024-07"

    Raises ValueError for invalid format.
    """
    try:
        datetime.strptime(month, "%Y-%m")
        return month
    except ValueError:
        raise ValueError(f"Formato de mês inválido: '{month}'. Esperado 'YYYY-MM'.")


def current_month_orders() -> str:
    """Return the current month in 'MM/yyyy' format for orders."""
    now = datetime.now()
    return now.strftime("%m/%Y")


def current_month_expenses() -> str:
    """Return the current month in 'YYYY-MM' format for expenses."""
    now = datetime.now()
    return now.strftime("%Y-%m")


def format_time_now() -> str:
    """Return current time in 'HH:mm' format for save messages."""
    return datetime.now().strftime("%H:%M")
```

**Key details:**
- All functions are pure (no side effects).
- `parse_month_for_orders` returns `(int, int)` — the repository layer needs separate month and year for the date range query.
- `parse_month_for_expenses` validates and passes through — the repository uses the string directly.

---

### 2.13 `src/backend/utils/text.py` — Text Normalization

**Purpose:** ASCII normalization for fuzzy search.

```python
import unicodedata


def normalize_text(text: str) -> str:
    """
    Convert text to ASCII-normalized lowercase form for fuzzy matching.

    Algorithm (matching Rust unidecode behavior):
    1. Normalize Unicode to NFD (decomposed form).
    2. Strip combining characters (accents, diacritics).
    3. Remove non-ASCII characters.
    4. Lowercase the result.

    Examples:
        "Fornecedor com acento" → "fornecedor com acento"
        "São Paulo" → "sao paulo"
        "Gessofer" → "gessofe"  (if 'ç' is stripped)
        "Café" → "cafe"

    This matches the behavior of the `unidecode` crate used in the Rust backend.
    """
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if ord(c) < 128)
    return ascii_text.lower()
```

**Key details:**
- Uses `unicodedata.normalize("NFKD", ...)` — the Python equivalent of Rust's `unidecode`.
- **No external dependency needed** — `unicodedata` is in the Python standard library.

---

### 2.14 `src/backend/__init__.py` — Package Root

**Purpose:** Top-level package init — exports the public API surface for the data layer.

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

__all__ = [
    # Database
    "get_engine",
    "discover_database_path",
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
]
```

**Key details:**
- Removed exports for `init_database`, `get_connection`, and all custom exceptions (no longer in scope).
- Removed exports for `distribute_freight`, `save_orders` (service layer — out of scope).
- Removed exports for Tauri command functions (API layer — out of scope).

---

## 3. Database Module — Discovery and Engine

**Already detailed in section 2.2 above.**

**Summary:**
- **Discovery:** `discover_database_path()` checks `DATABASE_URL` → `%LOCALAPPDATA%\gessofer-tauri\main.db` → `%TEMP%\tmp-gessofer-tauri.db` in that order.
- **Engine:** `get_engine()` returns a SQLAlchemy `Engine` configured for SQLite with `StaticPool` and `check_same_thread=False`.
- **Schema:** The database schema is **assumed to already exist**. Tables are created externally (e.g., via migration scripts or manual SQL). There is no `init_database()` or `schema.sql`.
- **Lifecycle:** Callers create `Session` instances from the engine as needed: `with Session(engine) as session: ...`.

---

## 4. ORM Entities — SQLAlchemy Model Reference

| Entity | Table | Primary Key | Key Columns |
|--------|-------|-------------|-------------|
| `Order` | `ORDER` | `ID` (String) | `DATE` (Date), `SUPPLIER` (String), `SUPPLIER_NORMALIZED` (String), `NFE_KEY` (String, nullable), `FREIGHT` (Integer), `UNLOADING` (Integer), `CREATED_AT` (DateTime), `UPDATED_AT` (DateTime) |
| `Product` | `PRODUCT` | `ID` (String) | `NAME` (String), `NAME_NORMALIZED` (String), `QUANTITY` (Integer), `PRICE` (Integer), `TOTAL_PRICE` (Integer), `ORDER_ID` (ForeignKey), `ITEM_ORDINAL` (Integer, nullable), `CREATED_AT` (DateTime), `UPDATED_AT` (DateTime) |
| `Expense` | `EXPENSE` | `ID` (Integer, autoincrement) | `MONTH` (String), `DESCRIPTION` (String), `VALUE` (Integer), `CREATED_AT` (DateTime), `UPDATED_AT` (DateTime) |

**Relationships:**
- `Order.products` → `List[Product]` (backref: `Product.order`)
- `Product.order` → `Order` (backref: `Order.products`)
- `Product.ORDER_ID` → `ForeignKey("ORDER.ID")`

**Column type mapping:**
- `String` → SQLite `TEXT`
- `Integer` → SQLite `INTEGER`
- `Date` → SQLite `DATE`
- `DateTime` → SQLite `DATETIME`
- `ForeignKey` → SQLite `TEXT` (references `ORDER.ID`)

---

## 5. DTO Models — Dataclass Reference

| DTO | Fields | Purpose |
|-----|--------|---------|
| `OrderInput` | `id`, `date`, `supplier`, `nfe_key`, `freight`, `unloading`, `products` | Input from UI to save orders |
| `ProductInput` | `id`, `name`, `quantity`, `price`, `total`, `order_id`, `item_ordinal` | Input from UI for a product line |
| `ExpenseInput` | `description`, `value` | Input from UI to save an expense |
| `PageResponse[T]` | `items`, `page`, `page_count`, `total`, `page_size` | Generic paginated query result |

**Key distinction:** DTOs are **plain dataclasses** — they are not ORM entities. They carry no SQLAlchemy decorators, no table mappings, and no relationships. They exist solely as the contract between the UI layer and the repository layer.

---

## 6. Repository Layer — SQLAlchemy Query Patterns

### 6.1 OrderRepository

| Method | Pattern | Description |
|--------|---------|-------------|
| `fetch_orders_for_month(month, year)` | `select(Order).where(...).order_by(...)` | Date range query for a calendar month |
| `search_products(page, supplier?, product?, month?)` | `select(Product).where(*dynamic_clauses).limit().offset()` | Paginated search with optional filters |
| `delete_orders(order_ids)` | `delete(Order).where(Order.ID.in_(...))` | Delete orders by UUIDs |
| `insert_order(order)` | `session.add(Order(...))` | Insert a new order row |
| `delete_order_products(order_ids)` | `delete(Product).where(Product.ORDER_ID.in_(...))` | Delete products for given order IDs |
| `insert_product(product)` | `session.add(Product(...))` | Insert a new product row |

### 6.2 ExpenseRepository

| Method | Pattern | Description |
|--------|---------|-------------|
| `fetch_expenses_for_month(month)` | `select(Expense).where(Expense.MONTH == month).order_by(...)` | Fetch expenses for a YYYY-MM month |
| `delete_expenses_for_month(month)` | `delete(Expense).where(Expense.MONTH == month)` | Delete all expenses for a month |
| `insert_expense(expense, month)` | `session.add(Expense(...))` | Insert a new expense row |

**Session lifecycle:**
- Callers are responsible for creating and managing `Session` instances.
- Typical pattern: `with Session(engine) as session: repo = OrderRepository(session); ...`
- The `Session` context manager handles commit on success, rollback on exception.

---

## 7. Utilities — Unchanged

The utility modules (`currency.py`, `date.py`, `text.py`) are **unchanged** from the original plan. They are pure functions with no dependencies on SQLAlchemy or the database layer.

---

## 8. requirements.txt Changes

**Add the following line to `requirements.txt`:**

```
SQLAlchemy==2.0.51
```

**Remaining dependencies (unchanged):**
- `PySide6==6.11.1` (existing)
- `SQLAlchemy==2.0.51` (new)

**Note:** SQLAlchemy replaces the raw `sqlite3` approach. All other utilities (currency, date, text) continue to use only the Python standard library (`unicodedata`, `datetime`, `dataclasses`, `os`, `pathlib`).

---

## 9. Implementation Order

The following sequence minimizes merge conflicts and ensures each step builds on a working foundation:

### Phase 1: Foundation (no dependencies)
1. **Create directories:** `src/backend/database/`, `src/backend/entities/`, `src/backend/models/`, `src/backend/repositories/`, `src/backend/utils/`
2. **`src/backend/__init__.py`** — Package init (empty or minimal)
3. **`src/requirements.txt`** — Add `SQLAlchemy==2.0.51`

### Phase 2: Utilities (no dependencies)
4. **`src/backend/utils/__init__.py`** — Package init
5. **`src/backend/utils/text.py`** — ASCII normalization
6. **`src/backend/utils/currency.py`** — Currency conversion
7. **`src/backend/utils/date.py`** — Date utilities

### Phase 3: Database Module (depends on nothing)
8. **`src/backend/database/__init__.py`** — Package init
9. **`src/backend/database/connection.py`** — `discover_database_path()` and `get_engine()`

### Phase 4: Entities (depends on SQLAlchemy package only)
10. **`src/backend/entities/__init__.py`** — Package init
11. **`src/backend/entities/orm.py`** — SQLAlchemy declarative models (Order, Product, Expense)

### Phase 5: DTO Models (no dependencies)
12. **`src/backend/models/__init__.py`** — Package init
13. **`src/backend/models/dto.py`** — Plain dataclass DTOs (OrderInput, ProductInput, ExpenseInput, PageResponse)

### Phase 6: Repositories (depends on entities, models, utils, database)
14. **`src/backend/repositories/__init__.py`** — Package init
15. **`src/backend/repositories/expense_repository.py`** — Simpler, do first
16. **`src/backend/repositories/order_repository.py`** — More complex, do second

### Phase 7: Package Root Wiring
17. **Update `src/backend/__init__.py`** — Wire all public exports (entities, DTOs, repositories, utils, database)

---

## 10. Verification Steps

### 10.1 Unit Tests for Utilities

**Test `normalize_text`:**
```python
assert normalize_text("São Paulo") == "sao paulo"
assert normalize_text("Fornecedor com acento") == "fornecedor com acento"
assert normalize_text("Gessofer") == "gessofe"
assert normalize_text("Café") == "cafe"
assert normalize_text("Ação") == "acao"
```

**Test `cents_to_display`:**
```python
assert cents_to_display(123456) == "1.234,56"
assert cents_to_display(99) == "0,99"
assert cents_to_display(0) == "0,00"
assert cents_to_display(100) == "1,00"
assert cents_to_display(1000) == "10,00"
assert cents_to_display(10000) == "100,00"
assert cents_to_display(100000) == "1.000,00"
assert cents_to_display(-123456) == "-1.234,56"
```

**Test `parse_currency_to_cents`:**
```python
assert parse_currency_to_cents("1.234,56") == 123456
assert parse_currency_to_cents("0,99") == 99
assert parse_currency_to_cents("0,00") == 0
assert parse_currency_to_cents("") == 0
assert parse_currency_to_cents("123456") == 123456
assert parse_currency_to_cents("1234,56") == 123456
```

**Test `parse_month_for_orders`:**
```python
assert parse_month_for_orders("07/2024") == (7, 2024)
assert parse_month_for_orders("12/2025") == (12, 2025)
# Should raise ValueError for "2024-07" (wrong format)
```

**Test `br_date_to_iso` / `iso_to_br_date`:**
```python
assert br_date_to_iso("24/07/2024") == "2024-07-24"
assert iso_to_br_date("2024-07-24") == "24/07/2024"
assert br_date_to_iso("invalid") == ""
assert iso_to_br_date("invalid") == ""
```

### 10.2 SQLAlchemy Entity Tests (Optional)

**Test: Entity column definitions:**
```python
from backend.entities.orm import Order, Product, Expense
from sqlalchemy import inspect

# Verify Order table columns
order_cols = {c.name for c in inspect(Order).columns}
assert "ID" in order_cols
assert "DATE" in order_cols
assert "SUPPLIER" in order_cols
assert "SUPPLIER_NORMALIZED" in order_cols
assert "NFE_KEY" in order_cols
assert "FREIGHT" in order_cols
assert "UNLOADING" in order_cols
assert "CREATED_AT" in order_cols
assert "UPDATED_AT" in order_cols
assert "products" in {r.property.key for r in inspect(Order).relationships}

# Verify Product table columns
product_cols = {c.name for c in inspect(Product).columns}
assert "ID" in product_cols
assert "NAME" in product_cols
assert "ORDER_ID" in product_cols
assert "ITEM_ORDINAL" in product_cols

# Verify Expense table columns
expense_cols = {c.name for c in inspect(Expense).columns}
assert "ID" in expense_cols
assert "MONTH" in expense_cols
assert "DESCRIPTION" in expense_cols
assert "VALUE" in expense_cols
```

**Test: SQLAlchemy engine creation:**
```python
import tempfile, os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

# Create a temp DB file
tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"

from backend.database.connection import get_engine
engine = get_engine()
assert engine is not None

# Verify WAL mode is set
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("PRAGMA journal_mode"))
    assert result.scalar() == "wal"

os.unlink(tmp.name)
```

---

## 11. Risks and Considerations

### 11.1 SQLAlchemy Column Name Case

**Risk:** SQLAlchemy by default lowercases column names in the `__table_args__` or maps them to the table. When using `mapped_column("COLUMN_NAME", ...)`, the string name maps to the actual DB column, but the Python attribute is `COLUMN_NAME` (uppercase). This is correct for our case since we want to preserve the exact DB column names.

**Mitigation:** All column names in the ORM entities use the exact uppercase names from the original schema. The `mapped_column("NAME", ...)` first argument is the DB column name, and the Python attribute name matches it.

### 11.2 Database Schema Assumption

**Risk:** The backend assumes tables already exist. If the database file is new or corrupted, queries will fail with `OperationalError: no such table`.

**Mitigation:** The application startup should verify the database exists and tables are present. If not, the user should be prompted to restore from backup or run a migration script. The `discover_database_path()` function raises `FileNotFoundError` if no DB is found, which the UI can handle.

### 11.3 SQLite Thread Safety with StaticPool

**Risk:** SQLite does not support concurrent writes. Using `StaticPool` with `check_same_thread=False` is necessary for desktop apps but could cause issues if multiple threads write simultaneously.

**Mitigation:** The desktop app is single-user and typically single-threaded for DB operations. When integrating with QML, ensure all DB operations go through a single thread (e.g., via a QObject worker).

### 11.4 ORM Entity vs DTO Separation

**Risk:** Developers may confuse ORM entities (in `entities/`) with DTOs (in `models/`). ORM entities map to DB tables and use SQLAlchemy decorators; DTOs are plain dataclasses for UI input/output.

**Mitigation:** Clear naming (`orm.py` vs `dto.py`), clear documentation in each file, and the directory structure itself (`entities/` vs `models/`) reinforces the distinction.

### 11.5 SQLAlchemy 2.0 Migration

**Risk:** SQLAlchemy 2.0 introduced breaking changes from the 1.x style (`session.query()` → `session.execute(select())`). The code must use the 2.0 style consistently.

**Mitigation:** All repository code uses `session.execute(select(...)).scalars().all()` pattern. No legacy `session.query()` calls are present.

### 11.6 Date Type Mapping

**Risk:** SQLAlchemy's `Date` type maps to SQLite's `DATE` storage, which is stored as TEXT. Python's `date` objects are automatically converted to/from ISO format strings when reading/writing.

**Mitigation:** The repository code uses `order.date` (a string in `YYYY-MM-DD` format from the DTO) and SQLAlchemy handles the conversion to/from `date` objects. For the `DATE` column in the ORM, we use `Date` type which maps Python `date` objects to SQLite date strings.

---

## 12. Appendix: Removed Scope

The following were explicitly **removed** from this plan per the refinement requirements:

- **`src/errors.py`** — Custom exception hierarchy (not part of database layer).
- **`src/backend/services/`** — Business logic services (freight distribution, save orchestration).
- **`src/backend/api/`** — Tauri-command equivalents (API/command layer).
- **`src/backend/database/schema.sql`** — DDL schema file (removed; schema is externally managed).
- **`init_database()`** — Schema initialization function (removed; no DDL creation).
- **Section: Data Model Changes** — ORM entity details moved to Section 4 (Entities reference); DTO models remain in Section 5.
- **Section: API Changes** — Removed entirely (out of scope).
- **Section: State Management** — Removed entirely (out of scope).
- **Section: Error Handling** — Removed entirely (no custom exceptions).
- **Section: Appendix: SQL Queries** — Removed entirely (SQLAlchemy handles SQL generation).
- **Freight distribution tests** — Removed (service layer out of scope).
- **Integration tests for repositories** — Removed (simplified to SQLAlchemy pattern examples).
- **End-to-end tests** — Removed (API layer out of scope).
