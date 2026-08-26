> **Part of:** [Gessofer-Tauri Documentation](README.md)

# Migration Mapping (for Python Port)

## 10.1 Vue → PySide6 Component Mapping

| Vue Component | PySide6 Equivalent | Notes |
|--------------|-------------------|-------|
| `App.vue` (root layout) | `QMainWindow` + `QStackedWidget` | Main window with stacked pages for routing |
| `AppNavbar.vue` | `QMenuBar` or `QToolBar` | Navigation menu with dropdowns |
| `ProductList.vue` | Custom `QWidget` with `QTableWidget` + `QFormLayout` | Product list with filters |
| `OrderEdit.vue` | Custom `QWidget` with dynamic `QFormLayout` rows | Most complex — dynamic form rows |
| `ExpensesView.vue` | Custom `QWidget` with `QTableWidget` | Simple expense display |
| `ExpensesEdit.vue` | Custom `QWidget` with dynamic rows | Expense editor |
| `AboutView.vue` | Simple `QLabel`/`QDialog` | Placeholder page |
| `DataTable.vue` | `QTableWidget` | Generic table with custom delegates |
| `FormInput.vue` | `QLineEdit` + `QLabel` + `QValidator` | Reusable form field |
| `MonthQueryForm.vue` | `QLineEdit` (masked) + `QPushButton` | Month selector |
| `AlertContainer.vue` | `QMessageBox` or custom `QFrame` overlay | Toast/alert notifications |
| `MessageContainer.vue` | `QLabel` with styled stylesheet | Success/error messages |
| `FoundationTooltip.vue` | `QToolTip.show()` or `QWhatsThis` | Hover tooltips |
| `ExpensesTable.vue` | `QTableWidget` with custom delegate | Expenses display |

## 10.2 Pinia Store → PyQt Signal/Slot Mapping

| Pinia Store | PyQt5/PySide6 Equivalent |
|------------|-------------------------|
| `useAlertStore` (global reactive state) | Custom `QObject` with signals, or a singleton class with `pyqtSignal` |
| `ref()` / `reactive()` | `QProperty` via `QObject` or simple Python `property` |
| `defineStore("alert", () => { ... })` | `class AlertManager(QObject):` with `alertShown = pyqtSignal(str, str)` |
| `useField()` (vee-validate field state) | `QLineEdit.textChanged` signal + validator |
| `useFieldArray()` (dynamic array) | `QListWidget` or `QTableWidget` with dynamic row insertion/removal |

**Example Alert Store Replacement:**
```python
class AlertManager(QObject):
    alertShown = pyqtSignal(str, str)  # (type, text)
    
    def __init__(self):
        super().__init__()
        self._display = False
        self._text = ""
        self._type = "primary"
    
    def show_alert(self, alert_type: str, text: str):
        self._type = alert_type
        self._text = text
        self._display = True
        self.alertShown.emit(alert_type, text)
        QTimer.singleShot(10000, self.hide_alert)  # 10 seconds
    
    def hide_alert(self):
        self._display = False
        self.alertShown.emit(self._type, self._text)
```

## 10.3 Tauri Commands → Python Backend Mapping

| Tauri Command | Python Equivalent | Implementation |
|--------------|-------------------|---------------|
| `orders_for_month(month)` | `def get_orders_for_month(month: str) -> list[Order]` | SQLite query with date range filter |
| `product_list(page, supplier?, product?, month?)` | `def list_products(page: int, supplier: str, product: str, month: str) -> PageResponse` | SQLite query with LIMIT/OFFSET, LIKE for filtering |
| `save_orders(orders, deletedOrders)` | `def save_orders(orders: list[Order], deleted: list[str]) -> None` | SQLite transaction: DELETE + INSERT |
| `expenses_for_month(month)` | `def get_expenses_for_month(month: str) -> list[Expense]` | SQLite query with month filter |
| `save_expenses(expenses, month)` | `def save_expenses(expenses: list[Expense], month: str) -> None` | SQLite transaction: DELETE month + INSERT |

**Communication:** Instead of Tauri's IPC, use:
- **Option A:** Direct function calls (single-process Python app)
- **Option B:** `sqlite3` module for database access
- **Option C:** `SQLAlchemy` for ORM (if preferred over raw SQL)

## 10.4 SeaORM SQLite → Python SQLite Mapping

| SeaORM Feature | Python Equivalent |
|---------------|-------------------|
| `Entity` model (auto-generated) | `dataclass` or `SQLAlchemy` model |
| `DatabaseConnection` | `sqlite3.connect()` or `SQLAlchemy.create_engine()` |
| `Entity::find().filter().all()` | `cursor.execute("SELECT ... WHERE ...")` |
| `Entity::insert(model)` | `cursor.execute("INSERT INTO ...")` |
| `Entity::delete_many().filter()` | `cursor.execute("DELETE FROM ... WHERE ...")` |
| `find_also_related()` (join) | `JOIN` in SQL query |
| `find_with_related()` (nested) | `JOIN` + Python grouping |
| `PaginatorTrait` | `LIMIT ? OFFSET ?` in SQL |
| `ActiveValue::Set()` | Direct assignment in dataclass |
| `ActiveValue::NotSet` | Omit from INSERT |
| `TransactionTrait` | `connection.begin()` / `connection.commit()` / `connection.rollback()` |
| `Column::NameNormalized.like()` | `WHERE name_normalized LIKE '%...%'` |
| `Date` type | `datetime.date` |
| `DateTime` type | `datetime.datetime` |

**Recommended Python Libraries:**
| Purpose | Library | Alternative |
|---------|---------|-------------|
| Database access | `sqlite3` (stdlib) | `SQLAlchemy` (ORM) |
| Date handling | `datetime` (stdlib) | `dateutil` |
| UUID generation | `uuid` (stdlib) | — |
| Data classes | `dataclasses` (stdlib) | `pydantic` |
| Async (if needed) | `aiosqlite` | `tortoise-orm` |

## 10.5 Yup/vee-validate → Python Validation Mapping

| Yup Method | Python Equivalent | Library |
|-----------|-------------------|---------|
| `string().required()` | `if not value: raise ValidationError` | `pydantic` / `cerberus` |
| `string().dateFormat(format)` | Parse with `datetime.strptime(value, format)` | `datetime` |
| `string().currency()` | Regex `/^\d+([.,]\d+)?$/` | `re.match(r'^\d+([.,]\d+)?$', value)` |
| `string().integer()` | Regex `/^[0-9]*$/` | `re.match(r'^[0-9]*$', value)` |
| `requiredIfFilled(field)` | Cross-field validation | `pydantic.model_validator` |
| `array(schema)` | List validation | `pydantic.BaseModel` with `list[Item]` |
| `when(field, { is, then })` | Conditional validation | Custom validator logic |

**Recommended Python Validation Library:**
- **Primary:** `pydantic` — provides all Yup functionality plus more
- **Alternative:** `cerberus` — simpler, schema-based validation
- **Alternative:** `valideer` — lightweight, flexible validation

**Pydantic Example:**
```python
from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime

class ProductForm(BaseModel):
    id: str
    name: str
    quantity: str
    price: str
    total: str = ""
    warn: str = ""
    
    @field_validator("quantity")
    @classmethod
    def quantity_is_integer(cls, v):
        if v and not re.match(r"^[0-9]*$", v):
            raise ValueError("Valor inválido")
        return v
    
    @field_validator("price")
    @classmethod
    def price_is_currency(cls, v):
        if v and not re.match(r"^\d+([.,]\d+)?$", v):
            raise ValueError("Valor inválido")
        return v

class OrderForm(BaseModel):
    date: str
    supplier: str
    nfe_key: str = ""
    freight: str = ""
    unloading: str = ""
    products: list[ProductForm] = []
    
    @field_validator("date")
    @classmethod
    def date_is_valid(cls, v):
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Data inválida")
        return v
    
    @model_validator(mode="after")
    def validate_products(self):
        for i, product in enumerate(self.products):
            has_name = bool(product.name)
            has_qty = bool(product.quantity)
            has_price = bool(product.price)
            if has_name + has_qty + has_price not in (0, 3):
                raise ValueError(f"Product {i}: name, quantity, and price must all be filled or all empty")
        return self
```

## 10.6 Foundation Sites → Qt Stylesheet Mapping

| Foundation Class | Qt Stylesheet Equivalent |
|-----------------|-------------------------|
| `.grid-container` | `QWidget { max-width: 1200px; margin: 0 auto; }` |
| `.grid-x.grid-margin-x` | Layout with `QHBoxLayout`/`QVBoxLayout` + `setSpacing(10)` |
| `.cell.auto` | `setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)` |
| `.cell.shrink` | `setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)` |
| `.medium-3` | `setFixedWidth(25%)` or `setStretchFactor(widget, 3)` |
| `.button` | `QPushButton { padding: 8px 16px; border: none; ... }` |
| `.button.is-primary` | `background-color: #008cba; color: white;` |
| `.button.is-secondary` | `background-color: #e7e7e7; color: #333;` |
| `.callout` | `QFrame { padding: 10px; border-radius: 3px; ... }` |
| `.callout.secondary` | `background-color: #f0f0f0;` |
| `.form-error.is-visible` | `QLabel { color: red; font-size: 12px; }` |
| `.input-group` | `QHBoxLayout` with label + line edit + button |
| `.input-group-label` | `QLabel` with icon (FontAwesome or Qt icon) |
| `.input-group-field` | `QLineEdit` |
| `.input-group-button` | `QPushButton` in layout |
| `.pagination` | Custom widget with `QPushButton` × N |
| `.card` | `QFrame { border: 1px solid #ddd; border-radius: 3px; }` |
| `.card-section` | `QFrame` within card with padding |
| `.top-bar` | `QMenuBar` or custom `QWidget` with `QHBoxLayout` |
| `.dropdown.menu` | `QMenu` with `QAction` |
| `.alert-absolute` | Overlay `QWidget` with `setWindowFlags(Qt.FramelessWindowHint)` |
| `.label.success` | `QLabel { color: green; font-weight: bold; }` |
| `.label.alert` | `QLabel { color: red; font-weight: bold; }` |
| `.is-invalid-input` | `QLineEdit { border: 2px solid red; }` |

**Recommended Qt Styling Approach:**
- Use **QSS (Qt Stylesheets)** — CSS-like syntax for Qt widgets
- Consider **Qt Designer (.ui files)** for complex layouts
- Use **FontAwesome for Qt** or **Qt Awesome** for icon support

## 10.7 Luxon Date Library → Python datetime Mapping

| Luxon | Python Equivalent |
|-------|-------------------|
| `DateTime.now()` | `datetime.now()` |
| `DateTime.fromFormat(date, format)` | `datetime.strptime(date, format)` |
| `date.toFormat(format)` | `date.strftime(format)` |
| `date.isValid` | `try: datetime.strptime(...)` / catch `ValueError` |
| `date.toFormat("yyyy-MM-dd")` | `date.strftime("%Y-%m-%d")` |
| `date.toFormat("dd/MM/yyyy")` | `date.strftime("%d/%m/%Y")` |
| `date.toFormat("HH:mm")` | `date.strftime("%H:%M")` |
| `date.toFormat("MM/yyyy")` | `date.strftime("%m/%Y")` |
| `DateTime` (immutable) | `datetime` (immutable) or `date` / `time` |

**Format Conversion Table:**
| Luxon Format | Python strftime |
|-------------|-----------------|
| `yyyy` | `%Y` |
| `MM` | `%m` |
| `dd` | `%d` |
| `HH` | `%H` |
| `mm` | `%M` |

**Example Replacement:**
```python
# Luxon
const date = DateTime.fromFormat("24/07/2024", "dd/MM/yyyy");
const iso = date.toFormat("yyyy-MM-dd");

# Python
from datetime import datetime
date = datetime.strptime("24/07/2024", "%d/%m/%Y")
iso = date.strftime("%Y-%m-%d")
```

## 10.8 Inputmask → Qt QLineEdit Mapping

| Inputmask | Qt Equivalent |
|-----------|--------------|
| `new Inputmask("99/9999")` | `QRegExpValidator(QRegExp(r"\d\d/\d{4}"), line_edit)` |
| `new Inputmask("99/99/9999")` | `QRegExpValidator(QRegExp(r"\d\d/\d\d/\d{4}"), line_edit)` |
| Mask auto-insertion | `QInputMask("99/9999")` or `QInputMask("99/99/9999")` |
| Mask validation | `QValidator.validate()` returns `Valid`/`Intermediate`/`Invalid` |

**Recommended Qt Approach:**
```python
from PySide6.QtWidgets import QLineEdit
from PySide6.QtGui import QInputMask, QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression

# Option 1: QInputMask (auto-inserts separators)
month_input = QLineEdit()
month_input.setInputMask("99/9999")  # Automatically adds "/"
# Note: QInputMask uses "9" for required digit, "0" for optional

date_input = QLineEdit()
date_input.setInputMask("99/99/9999")

# Option 2: QRegularExpressionValidator (custom validation)
regex = QRegularExpression(r"^\d{2}/\d{4}$")
validator = QRegularExpressionValidator(regex, month_input)
month_input.setValidator(validator)
```

**Note:** `QInputMask` is the closest equivalent to Inputmask — it provides automatic character insertion and format enforcement at the widget level.
