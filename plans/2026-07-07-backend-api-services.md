# Implementation Plan: API and Service Layer for Gessofer-Qt Python Backend

## Summary

This plan details the creation of the **API layer** (thin command functions that the QML frontend calls) and the **Service layer** (all business logic: save orchestration, freight distribution, XML import, validation) for the Gessofer-Qt desktop application. The existing data layer (`src/backend/`) provides the foundation — database connection, ORM entities, DTOs, repositories, and utilities. The API and Service layers sit on top of this foundation, providing the business logic and QML integration bridge.

---

## 1. Directory Structure

```
gessofer-qt/
├── src/
│   ├── main.py                          # Entry point (existing)
│   └── backend/
│       ├── __init__.py                  # Package init (existing; will be updated)
│       ├── errors.py                    # NEW: Custom exception hierarchy
│       ├── api/                         # NEW: API command functions
│       │   ├── __init__.py              # NEW: Package init
│       │   ├── orders.py                # NEW: orders_for_month + product_list
│       │   ├── save_orders.py           # NEW: save_orders command
│       │   └── save_expenses.py         # NEW: expenses_for_month + save_expenses
│       ├── services/                    # NEW: Business logic services
│       │   ├── __init__.py              # NEW: Package init
│       │   ├── save_order_service.py    # NEW: SaveOrderService + SaveExpenseService
│       │   ├── freight_distribution.py  # NEW: FreightDistributionService
│       │   ├── xml_import_service.py    # NEW: XmlImportService
│       │   └── validation_service.py    # NEW: ValidationService
│       ├── database/
│       │   ├── __init__.py              # Package init (existing)
│       │   └── connection.py            # DB discovery, engine (existing)
│       ├── entities/
│       │   ├── __init__.py              # Package init (existing)
│       │   └── orm.py                   # SQLAlchemy models (existing)
│       ├── models/
│       │   ├── __init__.py              # Package init (existing)
│       │   └── dto.py                   # Dataclass DTOs (existing)
│       ├── repositories/
│       │   ├── __init__.py              # Package init (existing)
│       │   ├── order_repository.py      # Order/Product queries (existing)
│       │   └── expense_repository.py    # Expense queries (existing)
│       └── utils/
│           ├── __init__.py              # Package init (existing)
│           ├── currency.py              # Currency conversion (existing)
│           ├── date.py                  # Date utilities (existing)
│           └── text.py                  # Text normalization (existing)
└── plans/
    └── 2026-07-07-backend-api-services.md  # THIS FILE
```

---

## 2. Files to Create

### 2.1 `src/backend/errors.py` — Custom Exception Hierarchy

**Purpose:** Define the `BackendError` exception hierarchy used throughout the API and service layers. Mirrors the Tauri-era `ApiError` pattern (user-facing message + detailed message).

**Full file contents:**

```python
from __future__ import annotations


class BackendError(Exception):
    """
    Base exception for all backend errors.

    Attributes:
        user_message: User-facing error message (in Portuguese).
        detail_message: Detailed error message for logging/debugging.
    """

    def __init__(self, user_message: str, detail_message: str = "") -> None:
        self.user_message: str = user_message
        self.detail_message: str = detail_message
        if detail_message:
            super().__init__(f"{user_message} ({detail_message})")
        else:
            super().__init__(user_message)


class ValidationError(BackendError):
    """Raised when input data fails validation."""

    def __init__(self, errors: list[str], detail_message: str = "") -> None:
        self.errors: list[str] = errors
        user_message = "; ".join(errors) if errors else "Dados inválidos"
        super().__init__(user_message, detail_message)


class DatabaseError(BackendError):
    """Raised when a database operation fails."""

    def __init__(self, detail_message: str) -> None:
        super().__init__("Erro no banco de dados", detail_message)


class XmlParseError(BackendError):
    """Raised when XML parsing fails or produces invalid data."""

    def __init__(self, message: str) -> None:
        super().__init__("Erro ao processar XML", message)
```

**Rationale:**
- `BackendError` is the base class — all other errors inherit from it.
- `ValidationError` carries a list of error strings so callers can display them individually.
- `DatabaseError` wraps SQLAlchemy exceptions with a generic user message.
- `XmlParseError` wraps XML parsing failures.
- All messages are in Brazilian Portuguese for user-facing display.
- The `detail_message` is intended for logging and debugging.

---

### 2.2 `src/backend/api/__init__.py` — API Package Init

**Purpose:** Export all public API functions for easy import.

**Full file contents:**

```python
from .orders import orders_for_month, product_list
from .save_orders import save_orders
from .save_expenses import expenses_for_month, save_expenses

__all__ = [
    "orders_for_month",
    "product_list",
    "save_orders",
    "expenses_for_month",
    "save_expenses",
]
```

---

### 2.3 `src/backend/api/orders.py` — Orders Query + Product List

**Purpose:** Thin API functions for querying orders and products. These functions receive raw input parameters, call the appropriate repository methods, and return results.

**Full file contents:**

```python
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.entities.orm import Order, Product
from backend.models.dto import PageResponse
from backend.repositories.order_repository import OrderRepository
from backend.utils.date import parse_month_for_orders


def orders_for_month(month: str) -> List[Order]:
    """
    Fetch all orders and their products for a given month.

    Args:
        month: Month string in 'MM/yyyy' format (e.g., '07/2024').

    Returns:
        List of Order ORM entities with products eagerly accessible.

    Raises:
        BackendError: If the month format is invalid or a database error occurs.
    """
    try:
        m, y = parse_month_for_orders(month)
    except ValueError as exc:
        raise ValueError(f"Formato de mês inválido: '{month}'. Esperado 'MM/yyyy'.") from exc

    engine = get_engine()
    with Session(engine) as session:
        repo = OrderRepository(session)
        return repo.fetch_orders_for_month(month=m, year=y)


def product_list(
    page: int = 1,
    supplier: Optional[str] = None,
    product: Optional[str] = None,
    month: Optional[str] = None,
) -> PageResponse[Product]:
    """
    Paginated product listing with optional filters.

    Args:
        page: Page number (1-based). Defaults to 1.
        supplier: Optional supplier name filter (fuzzy match).
        product: Optional product name filter (fuzzy match).
        month: Optional month filter in 'MM/yyyy' format.

    Returns:
        PageResponse with matching Product ORM entities.

    Raises:
        BackendError: If a database error occurs.
    """
    engine = get_engine()
    with Session(engine) as session:
        repo = OrderRepository(session)
        return repo.search_products(
            page=page,
            supplier=supplier,
            product=product,
            month=month,
        )
```

**Rationale:**
- Thin wrappers: they parse the month format (delegating to `parse_month_for_orders`), create a `Session`, instantiate the repository, and call the repository method.
- `orders_for_month` returns `List[Order]` — the QML layer can access `order.products` for each order.
- `product_list` returns `PageResponse[Product]` — the QML layer can access `response.items`, `response.page`, etc.
- Both functions use `with Session(engine) as session` for automatic commit/rollback.

---

### 2.4 `src/backend/api/save_orders.py` — Save Orders Command

**Purpose:** Thin API function that orchestrates the save-orders transaction by delegating to `SaveOrderService`.

**Full file contents:**

```python
from __future__ import annotations

from typing import List

from backend.models.dto import OrderInput
from backend.services.save_order_service import SaveOrderService


def save_orders(
    orders: List[OrderInput],
    deleted_orders: List[str],
) -> None:
    """
    Save orders in a single database transaction.

    This function is the API entry point for the 'save_orders' command.
    It delegates all business logic to SaveOrderService.

    Args:
        orders: List of OrderInput DTOs to save.
        deleted_orders: List of order UUIDs to delete.

    Raises:
        ValidationError: If input data fails validation.
        BackendError: If a database or transaction error occurs.
    """
    service = SaveOrderService()
    service.save_orders(orders=orders, deleted_order_ids=deleted_orders)
```

**Rationale:**
- Extremely thin: just instantiates the service and delegates.
- No validation, no transaction management, no error handling — all lives in `SaveOrderService`.
- This keeps the API layer purely a pass-through, making it easy to test and maintain.

---

### 2.5 `src/backend/api/save_expenses.py` — Expenses Query + Save

**Purpose:** Thin API functions for querying and saving expenses.

**Full file contents:**

```python
from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.entities.orm import Expense
from backend.models.dto import ExpenseInput
from backend.repositories.expense_repository import ExpenseRepository
from backend.services.save_order_service import SaveExpenseService
from backend.utils.date import parse_month_for_expenses


def expenses_for_month(month: str) -> List[Expense]:
    """
    Fetch all expenses for a given month.

    Args:
        month: Month string in 'YYYY-MM' format (e.g., '2024-07').

    Returns:
        List of Expense ORM entities.

    Raises:
        ValueError: If the month format is invalid.
        BackendError: If a database error occurs.
    """
    validated_month = parse_month_for_expenses(month)

    engine = get_engine()
    with Session(engine) as session:
        repo = ExpenseRepository(session)
        return repo.fetch_expenses_for_month(month=validated_month)


def save_expenses(
    expenses: List[ExpenseInput],
    month: str,
) -> None:
    """
    Save expenses in a single database transaction.

    This function is the API entry point for the 'save_expenses' command.
    It delegates all business logic to SaveExpenseService.

    Args:
        expenses: List of ExpenseInput DTOs to save.
        month: Month string in 'YYYY-MM' format.

    Raises:
        ValidationError: If input data fails validation.
        BackendError: If a database or transaction error occurs.
    """
    validated_month = parse_month_for_expenses(month)

    service = SaveExpenseService()
    service.save_expenses(expenses=expenses, month=validated_month)
```

**Rationale:**
- `expenses_for_month` is a thin query wrapper (similar to `orders_for_month`).
- `save_expenses` delegates to `SaveExpenseService` (a separate service class for expenses).

---

### 2.6 `src/backend/services/__init__.py` — Services Package Init

**Purpose:** Export all public service classes.

**Full file contents:**

```python
from .save_order_service import SaveOrderService, SaveExpenseService
from .freight_distribution import FreightDistributionService
from .xml_import_service import XmlImportService
from .validation_service import ValidationService

__all__ = [
    "SaveOrderService",
    "SaveExpenseService",
    "FreightDistributionService",
    "XmlImportService",
    "ValidationService",
]
```

---

### 2.7 `src/backend/services/save_order_service.py` — SaveOrderService + SaveExpenseService

**Purpose:** Business logic for saving orders and expenses in transactions. Implements the "delete all, insert all" strategy documented in the Tauri-era docs.

**Full file contents:**

```python
from __future__ import annotations

import logging
from typing import List

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
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
                validation_errors.append(f"ID de ordem vazio encontrado.")
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

        engine = get_engine()
        with Session(engine) as session:
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
                        f"Valor de despesa obrigatório quando descrição está preenchida."
                    )
                else:
                    validation_errors.append(
                        f"Descrição de despesa obrigatória quando valor está preenchido."
                    )

        if validation_errors:
            raise ValidationError(validation_errors, "Validação de despesas falhou.")

        engine = get_engine()
        with Session(engine) as session:
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

**Rationale:**
- `SaveOrderService` and `SaveExpenseService` are separate classes (single responsibility).
- Both use `with Session(engine) as session` for automatic commit/rollback.
- Validation is done inline (simple rules) — complex validation is delegated to `ValidationService`.
- Errors are wrapped in appropriate custom exceptions (`ValidationError`, `DatabaseError`).
- Logging is done at the service layer for error tracking.

---

### 2.8 `src/backend/services/freight_distribution.py` — FreightDistributionService

**Purpose:** Implements the proportional cost allocation algorithm from `docs/03-frontend-views.md` §3.2.3.

**Algorithm (verbatim from docs):**
```
1. freightTotal = parseCurrency(order.freight) + parseCurrency(order.unloading)
2. productsTotal = sum of all product.total values
3. ratio = (freightTotal + productsTotal) / productsTotal
4. For each product:
      newPrice = (product.total × ratio) / product.quantity
      newPrice = round(newPrice)
5. Set each product's price to the new value
6. The total for each product remains unchanged
```

**Full file contents:**

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from backend.models.dto import OrderInput, ProductInput

logger = logging.getLogger(__name__)


@dataclass
class FreightDistributionResult:
    """Result of a freight distribution calculation."""
    order_id: str
    old_freight: int
    old_unloading: int
    new_products: List[ProductInput]
    ratio: float
    products_total_before: int
    products_total_after: int


class FreightDistributionService:
    """
    Implements the proportional freight/unloading cost allocation algorithm.

    The algorithm redistributes freight + unloading costs across all products
    in an order proportionally to their total values.

    Key constraint: Only the unit PRICE is updated. The TOTAL for each product
    remains unchanged (total = price_before × quantity, used in the ratio
    calculation).
    """

    def distribute(
        self,
        order: OrderInput,
    ) -> FreightDistributionResult:
        """
        Distribute freight and unloading costs across all products in an order.

        Args:
            order: OrderInput with freight, unloading, and products.

        Returns:
            FreightDistributionResult with updated product prices and metadata.

        Raises:
            ValueError: If the order has no products or productsTotal is zero.
        """
        if not order.products:
            raise ValueError("Distribuição de frete requer pelo menos um produto.")

        products_total = sum(p.total for p in order.products)

        if products_total == 0:
            raise ValueError(
                "Distribuição de frete impossível: total de produtos é zero."
            )

        freight_total = order.freight + order.unloading
        ratio = (freight_total + products_total) / products_total

        new_products: list[ProductInput] = []
        for product in order.products:
            if product.quantity == 0:
                # Avoid division by zero — keep original price
                new_price = product.price
            else:
                new_price = round((product.total * ratio) / product.quantity)

            new_products.append(
                ProductInput(
                    id=product.id,
                    name=product.name,
                    quantity=product.quantity,
                    price=new_price,
                    total=product.total,  # Total remains unchanged
                    order_id=product.order_id,
                    item_ordinal=product.item_ordinal,
                )
            )

        products_total_after = sum(p.total for p in new_products)

        return FreightDistributionResult(
            order_id=order.id,
            old_freight=order.freight,
            old_unloading=order.unloading,
            new_products=new_products,
            ratio=ratio,
            products_total_before=products_total,
            products_total_after=products_total_after,
        )

    def apply_to_order(
        self,
        order: OrderInput,
    ) -> OrderInput:
        """
        Apply freight distribution to an order and return a new OrderInput.

        This is a convenience method that calls distribute() and returns
        a new OrderInput with the updated products.

        Args:
            order: OrderInput with freight, unloading, and products.

        Returns:
            A new OrderInput with updated product prices.
        """
        result = self.distribute(order)
        return OrderInput(
            id=result.order_id,
            date="",  # Preserved from original
            supplier="",  # Preserved from original
            nfe_key="",  # Preserved from original
            freight=result.old_freight,
            unloading=result.old_unloading,
            products=result.new_products,
        )
```

**Rationale:**
- `distribute()` returns a `FreightDistributionResult` dataclass with metadata (ratio, totals before/after) for UI feedback.
- `apply_to_order()` is a convenience wrapper that returns a new `OrderInput` with updated products.
- The algorithm preserves the original `total` for each product — only `price` changes.
- Division by zero is handled: if `quantity == 0`, the original price is kept.
- The `ratio` is computed as `(freightTotal + productsTotal) / productsTotal` — this is the key formula from the docs.

**Example verification (from docs §3.2.3):**
```
Freight: 1000, Unloading: 3000 → freightTotal = 4000
Products: qty=100, total=15000; qty=1, total=1000; qty=3, total=3015
productsTotal = 19015
ratio = (4000 + 19015) / 19015 ≈ 1.2104
Item 1: newPrice = (15000 * 1.2104) / 100 = 181.56 → 182
Item 2: newPrice = (1000 * 1.2104) / 1 = 1210.4 → 1210
Item 3: newPrice = (3015 * 1.2104) / 3 = 1216.4 → 1216
```

---

### 2.9 `src/backend/services/xml_import_service.py` — XmlImportService

**Purpose:** Parses NFe (Nota Fiscal Eletrônica) XML files and extracts order + product data. Uses `xml.etree.ElementTree` (stdlib).

**Full file contents:**

```python
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from xml.etree import ElementTree as ET

from backend.errors import XmlParseError
from backend.models.dto import OrderInput, ProductInput
from backend.utils.currency import parse_currency_to_cents
from backend.utils.date import br_date_to_iso

logger = logging.getLogger(__name__)

# NFe XML namespace
NFE_NS = "http://www.portalfiscal.inf.br/nfe"


@dataclass
class XmlImportResult:
    """Result of an XML import operation."""
    orders: List[OrderInput]
    warnings: List[str]


class XmlImportService:
    """
    Parses NFe (Nota Fiscal Eletrônica) XML files and extracts order + product data.

    Extracts:
    - Order-level: nfeKey, supplier, date
    - Product-level: name, quantity, price (adjusted for IPI/ICMS-ST), total

    Per docs §3.2.5:
    - vIPI and vICMS-ST are added to the base price.
    - If quantity is non-integer, a warning is generated and quantity is set to 0.
    - Warnings are space-separated strings.
    """

    def parse_file(self, file_path: str) -> XmlImportResult:
        """
        Parse a single NFe XML file.

        Args:
            file_path: Path to the XML file.

        Returns:
            XmlImportResult with parsed orders and warnings.

        Raises:
            XmlParseError: If the XML cannot be parsed or is not a valid NFe.
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError as exc:
            raise XmlParseError(f"Erro de parsing XML: {exc}") from exc
        except FileNotFoundError as exc:
            raise XmlParseError(f"Arquivo não encontrado: {file_path}") from exc

        return self._parse_nfe_root(root)

    def parse_string(self, xml_content: str) -> XmlImportResult:
        """
        Parse NFe XML content from a string.

        Args:
            xml_content: XML string content.

        Returns:
            XmlImportResult with parsed orders and warnings.

        Raises:
            XmlParseError: If the XML cannot be parsed or is not a valid NFe.
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            raise XmlParseError(f"Erro de parsing XML: {exc}") from exc

        return self._parse_nfe_root(root)

    def _parse_nfe_root(self, root: ET.Element) -> XmlImportResult:
        """Parse the root element of an NFe XML document."""
        warnings: list[str] = []

        # Find the NFe element (may be nested under infNFe, nFe, etc.)
        nfe = self._find_nfe_element(root)
        if nfe is None:
            raise XmlParseError("Documento não é uma NFe válida.")

        # Extract order-level data
        nfe_key = self._extract_text(nfe, "chNFe") or ""
        supplier = self._extract_emit_name(nfe) or ""
        date_raw = self._extract_text(nfe, "dhEmi") or ""
        date_iso = self._extract_date(date_raw)

        # Extract products
        products = self._extract_products(nfe, warnings)

        # Create a single order from the NFe
        order_id = str(uuid.uuid4())
        order = OrderInput(
            id=order_id,
            date=date_iso,
            supplier=supplier,
            nfe_key=nfe_key,
            freight=0,
            unloading=0,
            products=products,
        )

        return XmlImportResult(orders=[order], warnings=warnings)

    def parse_multiple_files(self, file_paths: List[str]) -> XmlImportResult:
        """
        Parse multiple NFe XML files and combine results into a single list of orders.

        Args:
            file_paths: List of file paths to parse.

        Returns:
            XmlImportResult with all parsed orders and combined warnings.
        """
        all_orders: list[OrderInput] = []
        all_warnings: list[str] = []

        for file_path in file_paths:
            result = self.parse_file(file_path)
            all_orders.extend(result.orders)
            all_warnings.extend(result.warnings)

        return XmlImportResult(orders=all_orders, warnings=all_warnings)

    def _find_nfe_element(self, root: ET.Element) -> Optional[ET.Element]:
        """Find the NFe root element, handling various XML structures."""
        # Try direct child
        for tag in ["NFe", "nfe", "infNFe"]:
            elem = root.find(f".//{{{NFE_NS}}}{tag}")
            if elem is not None:
                return elem

        # Try by local name (namespace-agnostic)
        for child in root:
            local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local_name in ("NFe", "nfe", "infNFe"):
                return child

        return None

    def _extract_text(self, parent: ET.Element, path: str) -> Optional[str]:
        """Extract text content from a child element by path."""
        elem = parent.find(f".//{{{NFE_NS}}}{path}")
        if elem is not None and elem.text:
            return elem.text.strip()
        return None

    def _extract_emit_name(self, nfe: ET.Element) -> Optional[str]:
        """Extract the supplier/company name from emit/xNome."""
        emit = nfe.find(f".//{{{NFE_NS}}}emit")
        if emit is not None:
            xnome = emit.find(f".//{{{NFE_NS}}}xNome")
            if xnome is not None and xnome.text:
                return xnome.text.strip()
        return None

    def _extract_date(self, date_raw: str) -> str:
        """Extract and convert date from ISO 8601 to YYYY-MM-DD."""
        if not date_raw:
            return ""
        # Take first 10 characters (YYYY-MM-DD)
        date_str = date_raw[:10]
        # Validate it's a valid date
        try:
            datetime.fromisoformat(date_str)
            return date_str
        except ValueError:
            return ""

    def _extract_products(self, nfe: ET.Element, warnings: list[str]) -> List[ProductInput]:
        """Extract product data from det elements."""
        products: list[ProductInput] = []

        # Find all det elements
        det_elements = nfe.findall(f".//{{{NFE_NS}}}det")

        for det in det_elements:
            # Extract product data from prod
            prod = det.find(f".//{{{NFE_NS}}}prod")
            if prod is None:
                continue

            x_prod = self._get_child_text(prod, "xProd") or ""
            v_prod_str = self._get_child_text(prod, "vProd") or "0"
            q_com_str = self._get_child_text(prod, "qCom") or "0"

            # Parse base price and quantity
            try:
                base_price = round(float(v_prod_str) * 100)  # to cents
            except ValueError:
                base_price = 0

            try:
                quantity = float(q_com_str)
            except ValueError:
                quantity = 0.0

            # Check if quantity is an integer
            if quantity != int(quantity):
                warnings.append("Quantidade não inteira.")
                quantity = 0

            quantity_int = int(quantity)

            # Extract IPI and ICMS-ST adjustments
            imposto = det.find(f".//{{{NFE_NS}}}imposto")
            ipi_value = 0
            icms_st_value = 0

            if imposto is not None:
                ipi_elem = imposto.find(f".//{{{NFE_NS}}}IPI")
                if ipi_elem is not None:
                    ipi_v_elem = ipi_elem.find(f".//{{{NFE_NS}}}vIPI")
                    if ipi_v_elem is not None and ipi_v_elem.text:
                        try:
                            ipi_value = round(float(ipi_v_elem.text) * 100)
                            if ipi_value > 0:
                                warnings.append("Produto com IPI.")
                        except ValueError:
                            pass

                icms_st_elem = imposto.find(f".//{{{NFE_NS}}}ICMSST")
                if icms_st_elem is not None:
                    v_elem = icms_st_elem.find(f".//{{{NFE_NS}}}vICMSST")
                    if v_elem is not None and v_elem.text:
                        try:
                            icms_st_value = round(float(v_elem.text) * 100)
                            if icms_st_value > 0:
                                warnings.append("Produto com ST.")
                        except ValueError:
                            pass

            # Calculate adjusted price
            adjusted_price = base_price + ipi_value + icms_st_value

            # Calculate unit price and total
            if quantity_int > 0:
                unit_price = adjusted_price // quantity_int
                total_price = adjusted_price
            else:
                unit_price = 0
                total_price = adjusted_price

            product_id = str(uuid.uuid4())

            product = ProductInput(
                id=product_id,
                name=x_prod,
                quantity=quantity_int,
                price=unit_price,
                total=total_price,
                order_id="",  # Will be set when order is created
                item_ordinal=None,
            )
            products.append(product)

        return products

    @staticmethod
    def _get_child_text(parent: ET.Element, child_tag: str) -> Optional[str]:
        """Get text content of a direct child element (namespace-agnostic)."""
        for child in parent:
            local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local_name == child_tag and child.text:
                return child.text.strip()
        return None
```

**Rationale:**
- `parse_file()` and `parse_string()` are the two public entry points (file path or raw XML content).
- `parse_multiple_files()` combines results from multiple XML files into a single `XmlImportResult`.
- The NFe XML namespace `http://www.portalfiscal.inf.br/nfe` is used for all XPath queries.
- IPI and ICMS-ST values are extracted from the `<imposto>` element and added to the base price.
- Quantity validation: if the quantity is not an integer, a warning is generated and quantity is set to 0.
- Warnings are accumulated in a list and returned alongside the orders.
- UUIDs are generated for order and product IDs (client-side generation, same as Tauri-era).
- The `_get_child_text` helper handles namespace-agnostic child element lookup for robustness.

---

### 2.10 `src/backend/services/validation_service.py` — ValidationService

**Purpose:** Implements cross-field validation rules from `docs/03-frontend-views.md` §3.2.8 and Appendix B.

**Validation rules:**
1. **Product validation:** name, quantity, price must all be filled or all empty (requiredIfFilled logic).
2. **Order validation:** date format valid, supplier required, all products valid.
3. **Expense validation:** description and value required together (both or neither).

**Full file contents:**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from backend.models.dto import ExpenseInput, OrderInput
from backend.utils.date import br_date_to_iso, parse_month_for_orders, parse_month_for_expenses


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ProductValidationResult:
    """Validation result for a single product."""
    valid: bool
    errors: list[str] = field(default_factory=list)


class ValidationService:
    """
    Implements cross-field validation rules for orders, products, and expenses.

    Validation rules (per docs §3.2.8 and Appendix B):
    1. Product: name, quantity, price must all be filled or all empty.
    2. Order: date valid format, supplier required, all products valid.
    3. Expense: description and value required together.
    """

    def validate_product(
        self,
        name: str,
        quantity: int,
        price: int,
    ) -> ProductValidationResult:
        """
        Validate a single product's core fields.

        Rule: name, quantity, price must all be filled or all empty.
        'Filled' means non-empty string (for name) or non-zero (for quantity/price).

        Args:
            name: Product name string.
            quantity: Product quantity (integer).
            price: Product unit price in cents (integer).

        Returns:
            ProductValidationResult with validity and error list.
        """
        errors: list[str] = []

        # Determine which fields are "filled"
        name_filled = bool(name and name.strip())
        quantity_filled = quantity != 0
        price_filled = price != 0

        # Count filled fields
        filled_count = sum([name_filled, quantity_filled, price_filled])

        if filled_count > 0 and filled_count < 3:
            # Some but not all fields are filled
            if not name_filled:
                errors.append("Nome do produto obrigatório quando outros campos estão preenchidos.")
            if not quantity_filled:
                errors.append("Quantidade do produto obrigatória quando outros campos estão preenchidos.")
            if not price_filled:
                errors.append("Preço do produto obrigatório quando outros campos estão preenchidos.")

        return ProductValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_order(
        self,
        order: OrderInput,
    ) -> ValidationResult:
        """
        Validate a single order.

        Rules:
        - Date must be in valid YYYY-MM-DD format.
        - Supplier must be non-empty.
        - All products must be valid.

        Args:
            order: OrderInput to validate.

        Returns:
            ValidationResult with validity and error list.
        """
        errors: list[str] = []

        # Validate date format
        if not order.date or not order.date.strip():
            errors.append("Data da ordem obrigatória.")
        else:
            converted = br_date_to_iso(order.date)
            if not converted:
                errors.append(f"Formato de data inválido: '{order.date}'. Use AAAA-MM-DD.")

        # Validate supplier
        if not order.supplier or not order.supplier.strip():
            errors.append("Fornecedor obrigatório.")

        # Validate products
        for i, product in enumerate(order.products):
            product_result = self.validate_product(product.name, product.quantity, product.price)
            if not product_result.valid:
                for err in product_result.errors:
                    errors.append(f"Produto {i + 1}: {err}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_expense(
        self,
        description: str,
        value: int,
    ) -> ValidationResult:
        """
        Validate a single expense.

        Rule: description and value must both be filled or both empty.

        Args:
            description: Expense description string.
            value: Expense value in cents.

        Returns:
            ValidationResult with validity and error list.
        """
        errors: list[str] = []

        desc_filled = bool(description and description.strip())
        value_filled = value != 0

        if desc_filled != value_filled:
            if desc_filled:
                errors.append("Valor da despesa obrigatório quando a descrição está preenchida.")
            else:
                errors.append("Descrição da despesa obrigatória quando o valor está preenchido.")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_orders(
        self,
        orders: List[OrderInput],
    ) -> ValidationResult:
        """
        Validate a list of orders.

        Args:
            orders: List of OrderInput to validate.

        Returns:
            ValidationResult with validity and combined error list.
        """
        all_errors: list[str] = []

        for i, order in enumerate(orders):
            order_result = self.validate_order(order)
            if not order_result.valid:
                for err in order_result.errors:
                    all_errors.append(f"Ordem {i + 1}: {err}")

        return ValidationResult(valid=len(all_errors) == 0, errors=all_errors)

    def validate_expenses(
        self,
        expenses: List[ExpenseInput],
    ) -> ValidationResult:
        """
        Validate a list of expenses.

        Args:
            expenses: List of ExpenseInput to validate.

        Returns:
            ValidationResult with validity and combined error list.
        """
        all_errors: list[str] = []

        for i, expense in enumerate(expenses):
            expense_result = self.validate_expense(expense.description, expense.value)
            if not expense_result.valid:
                for err in expense_result.errors:
                    all_errors.append(f"Despesa {i + 1}: {err}")

        return ValidationResult(valid=len(all_errors) == 0, errors=all_errors)
```

**Rationale:**
- `ValidationService` is stateless — all methods are pure functions (no side effects).
- `validate_product` implements the "requiredIfFilled" logic: if any of the three fields is filled, all three must be filled.
- `validate_order` checks date format, supplier, and delegates to `validate_product` for each product.
- `validate_expense` checks that description and value are both filled or both empty.
- `validate_orders` and `validate_expenses` aggregate results from individual validations.
- `ValidationResult` and `ProductValidationResult` are dataclasses that carry both validity and error details.

---

## 3. Files to Modify

### 3.1 `src/backend/__init__.py` — Update Package Root Exports

**Current state:** Exports data layer items (entities, DTOs, repositories, utils, database).

**Changes needed:**
- Add imports for `BackendError` and its subclasses from `errors`.
- Add imports for all service classes.
- Add imports for all API functions.
- Update `__all__` accordingly.

**Full updated file contents:**

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

---

## 4. QML Integration Strategy

### 4.1 BackendManager Singleton

Since this is a single-process Python app (no IPC, no Tauri), the QML frontend interacts with Python through **QObject wrapper classes** with `@Slot` decorators. The recommended pattern is a `BackendManager` singleton that the QML engine registers as a context property.

**Architecture:**
```
main.py (entry point)
    └── BackendManager (QObject singleton)
        ├── orders_for_month() → List[Order]  (via QAbstractListModel)
        ├── product_list() → PageResponse
        ├── save_orders() → None
        ├── expenses_for_month() → List[Expense]
        ├── save_expenses() → None
        ├── distribute_freight(order) → OrderInput
        ├── import_xml(file_path) → OrderInput
        ├── validate_order(order) → ValidationResult
        └── validate_expense(desc, value) → ValidationResult
        └── signals:
            ├── dataChanged() — emitted when data is loaded/updated
            ├── saveCompleted() — emitted on successful save
            └── errorOccurred(message) — emitted on error
```

**Implementation approach:**

1. **`src/backend/qml_backend.py`** — Contains the `BackendManager` QObject class and `QAbstractListModel` subclasses.

2. **`BackendManager`** exposes all API functions as `@Slot` methods:
   ```python
   from PySide6.QtCore import QObject, Signal, Slot, QUrl
   from PySide6.QtQml import qmlRegisterSingletonType

   class BackendManager(QObject):
       dataChanged = Signal()
       saveCompleted = Signal()
       errorOccurred = Signal(str)

       def __init__(self, parent: QObject | None = None) -> None:
           super().__init__(parent)

       @Slot(str)
       def orders_for_month(self, month: str) -> list:
           """Returns list of dicts (serializable to QML)."""
           ...

       @Slot(int, str, str, str)
       def product_list(self, page: int, supplier: str, product: str, month: str) -> dict:
           """Returns dict (serializable to QML)."""
           ...

       @Slot(str)
       def expenses_for_month(self, month: str) -> list:
           ...

       @Slot(list, list)
       def save_orders(self, orders: list, deleted_orders: list) -> None:
           ...

       @Slot(list, str)
       def save_expenses(self, expenses: list, month: str) -> None:
           ...
   ```

3. **`main.py`** registers the singleton:
   ```python
   # In main.py, after creating the engine:
   from backend.qml_backend import BackendManager

   backend = BackendManager()
   engine.rootContext().setContextProperty("BackendManager", backend)
   ```

4. **QML access:** Components access the backend via `BackendManager.orders_for_month("07/2024")` or connect to signals:
   ```qml
   Connections {
       target: BackendManager
       function onErrorOccurred(message) {
           // Show error message
       }
   }
   ```

### 4.2 Data Model Classes for QML

For list-based data (orders, expenses, products), create `QAbstractListModel` subclasses:

**`src/backend/qml_models.py`:**
```python
from PySide6.QtCore import QAbstractListModel, Qt, Signal, Slot
from PySide6.QtQml import qmlRegisterType

class OrderListModel(QAbstractListModel):
    """QML-accessible model for a list of orders."""
    role_names = {
        Qt.UserRole + 1: "id",
        Qt.UserRole + 2: "date",
        Qt.UserRole + 3: "supplier",
        Qt.UserRole + 4: "nfeKey",
        Qt.UserRole + 5: "freight",
        Qt.UserRole + 6: "unloading",
        Qt.UserRole + 7: "products",
    }

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._orders: list[dict] = []

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._orders)

    def data(self, index: QModelIndex, role: int = ...) -> any:
        if not index.isValid():
            return None
        order = self._orders[index.row()]
        role_name = self.role_names.get(role)
        if role_name:
            return order.get(role_name)
        return None

    @Slot(str)
    def load_for_month(self, month: str) -> None:
        """Load orders for a given month and update the model."""
        from backend.api.orders import orders_for_month
        from backend.utils.currency import cents_to_display
        from backend.utils.date import iso_to_br_date

        raw_orders = orders_for_month(month)
        # Convert ORM entities to dicts for QML
        self._orders = []
        for order in raw_orders:
            self._orders.append({
                "id": order.ID,
                "date": iso_to_br_date(order.DATE.isoformat()) if order.DATE else "",
                "supplier": order.SUPPLIER,
                "nfeKey": order.NFE_KEY or "",
                "freight": cents_to_display(order.FREIGHT),
                "unloading": cents_to_display(order.UNLOADING),
                "products": [
                    {
                        "id": p.ID,
                        "name": p.NAME,
                        "quantity": p.QUANTITY,
                        "price": cents_to_display(p.PRICE),
                        "total": cents_to_display(p.TOTAL_PRICE),
                        "order_id": p.ORDER_ID,
                        "itemOrdinal": p.ITEM_ORDINAL,
                    }
                    for p in order.products
                ],
            })
        self.reset()  # Notify QML of data change
```

**Key design decisions:**
- ORM entities are **converted to dicts** before being exposed to QML. This avoids issues with SQLAlchemy lazy loading in QML context.
- Currency values are converted from cents to display strings (`cents_to_display`) in the model layer.
- Dates are converted from ISO to BR format (`iso_to_br_date`) in the model layer.
- The `reset()` call after data update notifies QML to re-render.
- Product lists are nested dicts, accessible in QML as a `Repeater` or `ListView`.

### 4.3 Error Handling in QML

When API calls raise exceptions, the `BackendManager` catches them and emits the `errorOccurred` signal:

```python
@Slot(str)
def orders_for_month(self, month: str) -> list:
    try:
        return orders_for_month(month)
    except BackendError as exc:
        self.errorOccurred.emit(exc.user_message)
        return []
```

---

## 5. Implementation Order

### Phase 1: Foundation (errors + services package)
1. **Create `src/backend/errors.py`** — Exception hierarchy (no dependencies).
2. **Create `src/backend/services/__init__.py`** — Package init.
3. **Create `src/backend/services/validation_service.py`** — ValidationService (no dependencies, pure logic).

### Phase 2: Core Services (depend on errors + data layer)
4. **Create `src/backend/services/freight_distribution.py`** — FreightDistributionService (depends on models/dto.py).
5. **Create `src/backend/services/save_order_service.py`** — SaveOrderService + SaveExpenseService (depends on repositories, errors, models).
6. **Create `src/backend/services/xml_import_service.py`** — XmlImportService (depends on models/dto.py, errors, utils).

### Phase 3: API Layer (depend on services + data layer)
7. **Create `src/backend/api/__init__.py`** — Package init.
8. **Create `src/backend/api/orders.py`** — orders_for_month + product_list (depends on repositories, utils).
9. **Create `src/backend/api/save_orders.py`** — save_orders (depends on services).
10. **Create `src/backend/api/save_expenses.py`** — expenses_for_month + save_expenses (depends on repositories, services, utils).

### Phase 4: QML Integration (depends on everything above)
11. **Create `src/backend/qml_backend.py`** — BackendManager QObject singleton.
12. **Create `src/backend/qml_models.py`** — QAbstractListModel subclasses.
13. **Update `src/main.py`** — Register BackendManager as QML context property.

### Phase 5: Package Wiring
14. **Update `src/backend/__init__.py`** — Wire all new exports.

---

## 6. Verification Steps

### 6.1 Unit Tests for ValidationService

```python
# test_validation_service.py
from backend.services.validation_service import ValidationService
from backend.models.dto import OrderInput, ProductInput, ExpenseInput

svc = ValidationService()

# --- Product validation ---

# All filled → valid
result = svc.validate_product("Cimento", 100, 5000)
assert result.valid is True
assert result.errors == []

# All empty → valid
result = svc.validate_product("", 0, 0)
assert result.valid is True
assert result.errors == []

# Only name filled → invalid
result = svc.validate_product("Cimento", 0, 0)
assert result.valid is False
assert len(result.errors) == 2  # quantity and price errors

# Only quantity filled → invalid
result = svc.validate_product("", 100, 0)
assert result.valid is False
assert len(result.errors) == 2  # name and price errors

# --- Order validation ---

order = OrderInput(
    id="test-1",
    date="2024-07-24",
    supplier="Fornecedor Teste",
    nfe_key="12345678901234567890123456789012345678901234",
    freight=1000,
    unloading=2000,
    products=[
        ProductInput(id="p1", name="Cimento", quantity=100, price=5000, total=500000, order_id="test-1"),
    ],
)
result = svc.validate_order(order)
assert result.valid is True

# Invalid date → invalid
order.date = "24/07/2024"  # BR format — should fail (expects YYYY-MM-DD)
result = svc.validate_order(order)
assert result.valid is False

# Empty supplier → invalid
order.date = "2024-07-24"
order.supplier = ""
result = svc.validate_order(order)
assert result.valid is False

# --- Expense validation ---

# Both filled → valid
result = svc.validate_expense("Material de escritório", 50000)
assert result.valid is True

# Both empty → valid
result = svc.validate_expense("", 0)
assert result.valid is True

# Description filled, value empty → invalid
result = svc.validate_expense("Material de escritório", 0)
assert result.valid is False

# Description empty, value filled → invalid
result = svc.validate_expense("", 50000)
assert result.valid is False
```

### 6.2 Unit Tests for FreightDistributionService

```python
# test_freight_distribution.py
from backend.services.freight_distribution import FreightDistributionService
from backend.models.dto import OrderInput, ProductInput

svc = FreightDistributionService()

# Example from docs §3.2.3
order = OrderInput(
    id="test-1",
    date="2024-07-24",
    supplier="Fornecedor Teste",
    nfe_key="",
    freight=1000,
    unloading=3000,
    products=[
        ProductInput(id="p1", name="Produto A", quantity=100, price=150, total=15000, order_id="test-1"),
        ProductInput(id="p2", name="Produto B", quantity=1, price=1000, total=1000, order_id="test-1"),
        ProductInput(id="p3", name="Produto C", quantity=3, price=1005, total=3015, order_id="test-1"),
    ],
)

result = svc.distribute(order)

# ratio = (4000 + 19015) / 19015 ≈ 1.2104
assert abs(result.ratio - 1.21038...) < 0.001
assert result.products_total_before == 19015
assert result.old_freight == 1000
assert result.old_unloading == 3000

# Verify new prices
assert result.new_products[0].price == 182   # (15000 * 1.2104) / 100 = 181.56 → 182
assert result.new_products[1].price == 1210  # (1000 * 1.2104) / 1 = 1210.4 → 1210
assert result.new_products[2].price == 1216  # (3015 * 1.2104) / 3 = 1216.4 → 1216

# Totals remain unchanged
assert result.new_products[0].total == 15000
assert result.new_products[1].total == 1000
assert result.new_products[2].total == 3015
```

### 6.3 Unit Tests for XmlImportService

```python
# test_xml_import_service.py
from backend.services.xml_import_service import XmlImportService
from backend.models.dto import OrderInput, ProductInput

svc = XmlImportService()

# Test with a minimal NFe XML string
xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe12345678901234567890123456789012345678901234">
      <emit><xNome>Fornecedor Teste LTDA</xNome></emit>
      <ide><dhEmi>2024-07-24T10:30:00-03:00</dhEmi></ide>
    </infNFe>
  </NFe>
  <infNFe>
    <det nItem="1">
      <prod>
        <xProd>Cimento CP-II</xProd>
        <vProd>150.00</vProd>
        <qCom>100.0000</qCom>
      </prod>
      <imposto>
        <IPI><vIPI>5.00</vIPI></IPI>
        <ICMSST><vICMSST>2.50</vICMSST></ICMSST>
      </imposto>
    </det>
  </infNFe>
</nfeProc>"""

result = svc.parse_string(xml_content)

assert len(result.orders) == 1
order = result.orders[0]
assert order.supplier == "Fornecedor Teste LTDA"
assert order.date == "2024-07-24"
assert len(order.products) == 1

product = order.products[0]
assert product.name == "Cimento CP-II"
assert product.quantity == 100
# base_price = 15000 cents (150.00 * 100)
# ipi = 500 cents (5.00 * 100)
# icms_st = 250 cents (2.50 * 100)
# adjusted = 15750 cents
# unit_price = 15750 // 100 = 157
assert product.price == 157
assert product.total == 15750

# Warnings should include IPI and ST
assert "Produto com IPI" in result.warnings
assert "Produto com ST" in result.warnings
```

### 6.4 Unit Tests for SaveOrderService (Mocked)

```python
# test_save_order_service.py
import pytest
from unittest.mock import MagicMock, patch
from backend.services.save_order_service import SaveOrderService
from backend.models.dto import OrderInput, ProductInput
from backend.errors import ValidationError

svc = SaveOrderService()

# Test with valid input (mocked Session)
orders = [
    OrderInput(
        id="test-1",
        date="2024-07-24",
        supplier="Fornecedor Teste",
        nfe_key="",
        freight=1000,
        unloading=2000,
        products=[
            ProductInput(id="p1", name="Cimento", quantity=100, price=5000, total=500000, order_id="test-1"),
        ],
    ),
]

with patch("backend.services.save_order_service.get_engine") as mock_get_engine:
    mock_session = MagicMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    with patch("backend.services.save_order_service.Session", return_value=mock_session):
        # Should not raise
        svc.save_orders(orders=orders, deleted_order_ids=[])

# Test with invalid input (empty supplier)
invalid_orders = [
    OrderInput(
        id="test-2",
        date="2024-07-24",
        supplier="",  # Empty supplier
        nfe_key="",
        freight=0,
        unloading=0,
        products=[],
    ),
]

with patch("backend.services.save_order_service.get_engine") as mock_get_engine:
    mock_session = MagicMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    with patch("backend.services.save_order_service.Session", return_value=mock_session):
        with pytest.raises(ValidationError):
            svc.save_orders(orders=invalid_orders, deleted_order_ids=[])
```

### 6.5 Integration Verification

After implementing the full layer:

1. **Start the app and verify data loads:**
   ```python
   # In main.py or a test script:
   from backend.api.orders import orders_for_month
   from backend.api.save_expenses import expenses_for_month
   
   orders = orders_for_month("07/2024")
   assert len(orders) >= 0  # May be empty if no data exists
   
   expenses = expenses_for_month("2024-07")
   assert len(expenses) >= 0
   ```

2. **Verify freight distribution:**
   ```python
   from backend.services.freight_distribution import FreightDistributionService
   from backend.models.dto import OrderInput, ProductInput
   
   svc = FreightDistributionService()
   order = OrderInput(...)  # Create test order
   result = svc.distribute(order)
   assert result.ratio > 1.0  # Should be > 1 when freight > 0
   ```

3. **Verify XML import:**
   ```python
   from backend.services.xml_import_service import XmlImportService
   
   svc = XmlImportService()
   result = svc.parse_string("<nfeProc>...</nfeProc>")  # Valid NFe XML
   assert len(result.orders) >= 1
   assert len(result.warnings) >= 0
   ```

---

## 7. Risks and Considerations

### 7.1 SQLAlchemy ORM Entities in QML

**Risk:** SQLAlchemy ORM entities cannot be directly serialized to QML. The `products` relationship on `Order` triggers lazy loading, which may fail in a non-DB-session context.

**Mitigation:** All ORM entities are converted to plain dicts in the `BackendManager` / `QAbstractListModel` layer before being exposed to QML. The `OrderListModel.load_for_month()` method handles this conversion explicitly.

### 7.2 Currency Display in QML

**Risk:** QML cannot natively display Brazilian currency format (`R$ 1.234,56`). Currency values stored as cents need to be converted to display strings.

**Mitigation:** The `OrderListModel` and `ExpenseListModel` convert cents to display strings using `cents_to_display()` during the ORM-to-dict conversion. QML receives pre-formatted strings.

### 7.3 Date Format Conversion

**Risk:** QML may use JavaScript Date objects, but the backend stores dates as `YYYY-MM-DD` strings and displays as `dd/MM/yyyy`.

**Mitigation:** The model layer handles all date conversions:
- Loading: `iso_to_br_date(order.DATE.isoformat())` converts to BR format for display.
- Saving: The QML layer sends `YYYY-MM-DD` strings (or the `BackendManager` converts from BR format using `br_date_to_iso()`).

### 7.4 Session Management

**Risk:** Each API function creates its own `Session` via `with Session(engine) as session`. This means each call is a separate transaction. For the save operations, the service layer handles the transaction internally.

**Mitigation:** The API functions use `with Session(engine) as session` for auto-commit/rollback. The service layer (SaveOrderService, SaveExpenseService) also uses `with Session(engine) as session` for their transaction management. This is consistent with the data layer plan.

### 7.5 QML Object Lifecycle

**Risk:** The `BackendManager` QObject is created in Python and exposed to QML. If the QML engine is destroyed before the Python object, or if the Python object is garbage collected while QML still references it, crashes may occur.

**Mitigation:** The `BackendManager` is stored as a local variable in `main.py` before creating the engine, ensuring it stays alive for the app's lifetime. It is set as a context property (`engine.rootContext().setContextProperty("BackendManager", backend)`), which also keeps a reference.

### 7.6 XML Namespace Handling

**Risk:** NFe XML files may have varying namespace declarations, self-closed tags, or additional wrapper elements.

**Mitigation:** The `_find_nfe_element` method tries multiple strategies:
1. Direct child with namespace.
2. Namespace-agnostic lookup by local name.
3. Nested element search via `.//` XPath.

The `_get_child_text` method also handles namespace-agnostic child lookup.

### 7.7 Division by Zero in Freight Distribution

**Risk:** If a product has `quantity == 0`, the formula `(product.total × ratio) / product.quantity` would divide by zero.

**Mitigation:** The service checks `if product.quantity == 0` and keeps the original price in that case. A warning could be added for this scenario.

### 7.8 Large XML Files

**Risk:** NFe XML files can be large (many products). Parsing with `ElementTree` loads the entire document into memory.

**Mitigation:** For typical NFe files (up to a few thousand products), `ElementTree` is sufficient. If performance becomes an issue, `iterparse()` could be used for streaming.

---

## 8. Appendix: Service Class Reference

### 8.1 SaveOrderService

| Method | Signature | Description |
|--------|-----------|-------------|
| `save_orders` | `(orders: List[OrderInput], deleted_order_ids: List[str]) -> None` | Orchestrates the "delete all, insert all" transaction for orders. |

### 8.2 SaveExpenseService

| Method | Signature | Description |
|--------|-----------|-------------|
| `save_expenses` | `(expenses: List[ExpenseInput], month: str) -> None` | Orchestrates the "delete month, insert all" transaction for expenses. |

### 8.3 FreightDistributionService

| Method | Signature | Description |
|--------|-----------|-------------|
| `distribute` | `(order: OrderInput) -> FreightDistributionResult` | Calculates proportional freight distribution and returns result with metadata. |
| `apply_to_order` | `(order: OrderInput) -> OrderInput` | Convenience method that returns a new OrderInput with updated prices. |

### 8.4 XmlImportService

| Method | Signature | Description |
|--------|-----------|-------------|
| `parse_file` | `(file_path: str) -> XmlImportResult` | Parse a single NFe XML file. |
| `parse_string` | `(xml_content: str) -> XmlImportResult` | Parse NFe XML from a string. |
| `parse_multiple_files` | `(file_paths: List[str]) -> XmlImportResult` | Parse multiple XML files and combine results. |

### 8.5 ValidationService

| Method | Signature | Description |
|--------|-----------|-------------|
| `validate_product` | `(name: str, quantity: int, price: int) -> ProductValidationResult` | Validate a single product's core fields. |
| `validate_order` | `(order: OrderInput) -> ValidationResult` | Validate a single order (date, supplier, products). |
| `validate_expense` | `(description: str, value: int) -> ValidationResult` | Validate a single expense (description/value together). |
| `validate_orders` | `(orders: List[OrderInput]) -> ValidationResult` | Validate a list of orders. |
| `validate_expenses` | `(expenses: List[ExpenseInput]) -> ValidationResult` | Validate a list of expenses. |

### 8.6 API Functions Reference

| Function | Signature | Description |
|----------|-----------|-------------|
| `orders_for_month` | `(month: str) -> List[Order]` | Fetch orders for a month (MM/yyyy). |
| `product_list` | `(page: int, supplier?: str, product?: str, month?: str) -> PageResponse[Product]` | Paginated product search. |
| `save_orders` | `(orders: List[OrderInput], deleted_orders: List[str]) -> None` | Save orders in a transaction. |
| `expenses_for_month` | `(month: str) -> List[Expense]` | Fetch expenses for a month (YYYY-MM). |
| `save_expenses` | `(expenses: List[ExpenseInput], month: str) -> None` | Save expenses in a transaction. |
