# Implementation Plan: Product List View (via "Pedidos" nav item)

## Summary

This plan implements the **Product List** view — the first functional view of the Gessofer-Qt application. It adds a `QAbstractTableModel`-based Python model, a QML `ProductList` component with filter form, data table, and pagination, and wires it into the main window's view-switching logic. The backend data layer already exists; the main gap is that the transformer must include order-level fields (`date`, `supplier`) on each product row.

---

## Critical Issue: Backend Data Gap

The `orm_product_to_dict` transformer (used by `product_page_to_dict`) only outputs `id`, `name`, `quantity`, `price`, `total`, `order_id`, `itemOrdinal`. **It does NOT include `date` or `supplier`**, which the Product List view requires. The `search_products` query selects only `Product` without eagerly loading the `order` relationship.

This must be fixed **before** the QML layer can display the table correctly. See **Section 1.1** for details.

---

## Files to Create

### `App/ProductList.qml`

**Purpose:** The Product List view component — the first functional screen of the app.

**Key contents:**
- A `Rectangle` root with `color: Constants.contentBg`, `anchors.fill: parent`
- A `ColumnLayout` with `anchors.fill: parent` and `anchors.margins: Constants.contentMargins`
- Three internal properties:
  - `property alias filterSupplier: supplierField.text` (or a dedicated property)
  - `property alias filterProduct: productField.text`
  - `property alias filterMonth: monthField.text`
  - `property int currentPage: 1`
  - `property int pageCount: 0`
  - `property bool isLoading: false`
- **Filter form section:** A `RowLayout` or `ColumnLayout` with three labeled `TextField` inputs and two buttons ("Consultar" and "Limpar")
- **Table section:** A `TableView` bound to a `ProductListModel` instance, with 6 columns
- **Pagination section:** Previous/Next buttons + page indicator text ("Página X de Y")

**Dependencies:** Imports `QtQuick`, `QtQuick.Controls`, `QtQuick.Layouts`, and `Constants` (via module import). Creates/uses `ProductListModel` registered in `qml_models.py`.

---

## Files to Modify

### 1. `src/backend/qml/qml_models.py` — Add `ProductListModel`

**Current state:** Contains `OrderListModel` (QAbstractListModel) and `ExpenseListModel` (QAbstractListModel). Both are list models for `ListView`-style rendering.

**Changes needed:**

Add a new class `ProductListModel(QAbstractTableModel)` after the existing classes. This must be a **table model** because `TableView` requires `QAbstractTableModel`.

**Role names (6 columns + 1 hidden for order ID):**

```python
role_names: dict[int, str] = {
    Qt.UserRole + 1: "date",         # dd/MM/yyyy
    Qt.UserRole + 2: "supplier",     # raw string
    Qt.UserRole + 3: "name",         # raw string
    Qt.UserRole + 4: "price",        # R$ X,XX (display-formatted)
    Qt.UserRole + 5: "totalPrice",   # R$ X,XX (display-formatted)
    Qt.UserRole + 6: "orderId",      # hidden — for future edit navigation
}
```

**Properties (via `Q_PROPERTY` or Python `@Property`):**
- `items: list[dict[str, Any]]` — the data rows (exposed as a property for debugging; the actual data comes from `data()` using role names)
- `currentPage: int` — the current page number (default 1)
- `pageCount: int` — total number of pages (default 0)

**Methods:**
- `refresh(page: int, supplier: str = "", product: str = "", month: str = "") -> None`
  - Calls `BackendManager.product_list(page, supplier, product, month)` via the QML context property
  - Parses the returned dict: `items`, `page`, `page_count`
  - Transforms each item:
    - `date` → `iso_to_br_date(item.date)` (the backend returns ISO format)
    - `supplier` → raw string
    - `name` → raw string
    - `price` → `cents_to_display(item.price)`
    - `totalPrice` → `cents_to_display(item.totalPrice)` (note: the backend key is `totalPrice` in the table spec, but the ORM field is `TOTAL_PRICE` → transformer key is `total`)
    - `orderId` → raw string
  - Calls `beginResetModel()` / `endResetModel()` for proper QML re-rendering
- `clear() -> None`
  - Sets all filter properties to empty strings
  - Resets to page 1
  - Calls `refresh(1)` with no filters
- `rowCount(parent: QModelIndex) -> int` — returns `len(self._items)`
- `columnCount(parent: QModelIndex) -> int` — returns `6` (or `7` if counting hidden `orderId`)
- `data(index: QModelIndex, role: int) -> Any` — maps role to field, returns formatted values

**Important:** The `refresh` method must call `BackendManager.product_list()` — the `@Slot` method already registered in `qml_backend.py`. This is a synchronous slot call from QML; the Python method returns the dict directly (not async), so it works well with QML's `Connections` or direct binding.

**Registration:** The model class should be registered with `qmlRegisterType(ProductListModel, "App.Backend", 1, 0, "ProductListModel")` so it can be instantiated from QML as `ProductListModel {}`.

---

### 2. `src/backend/qml/qml_transformers.py` — Fix `orm_product_to_dict`

**Current state:** `orm_product_to_dict` returns only product-level fields (`id`, `name`, `quantity`, `price`, `total`, `order_id`, `itemOrdinal`). No `date` or `supplier`.

**Changes needed:**

**Option A (preferred):** Create a new transformer function `product_list_item_to_dict(product: Product) -> dict[str, Any]` that includes order-level fields:

```python
def product_list_item_to_dict(product: Product) -> dict[str, Any]:
    """Transform a Product for the Product List view (includes order date/supplier)."""
    return {
        "date": product.order.DATE.isoformat() if product.order and product.order.DATE else "",
        "supplier": product.order.SUPPLIER if product.order else "",
        "name": product.NAME,
        "price": product.PRICE,             # integer cents (raw — model will format)
        "totalPrice": product.TOTAL_PRICE,  # integer cents (raw — model will format)
        "orderId": product.ORDER_ID,
    }
```

Then update `product_page_to_dict` to use this new transformer:

```python
def product_page_to_dict(response: PageResponse[Product]) -> dict[str, Any]:
    return {
        "items": [product_list_item_to_dict(p) for p in response.items],
        "page": response.page,
        "page_count": response.page_count,
        "total": response.total,
        "page_size": response.page_size,
    }
```

**Performance concern:** The `search_products` query in `order_repository.py` does not eagerly load `Product.order`. Accessing `product.order.DATE` will trigger N+1 lazy loads (one per product row). For 50 rows this is acceptable but not ideal.

**Recommended fix:** Add `selectinload(Product.order)` to the `search_products` query:

```python
from sqlalchemy.orm import selectinload

# In search_products, change the fetch query to:
query_stmt = (
    select(Product)
    .options(selectinload(Product.order))  # eager load parent order
    .where(*where_clauses) if where_clauses else select(Product)
    .order_by(Product.NAME.asc())
    .limit(PAGE_SIZE)
    .offset(offset)
)
```

This ensures a single JOIN query instead of N+1 queries.

---

### 3. `src/backend/repositories/order_repository.py` — Eager-load Order in `search_products`

**Current state:** The `search_products` query uses `select(Product)` without `selectinload(Product.order)`.

**Changes needed:**
- Add `from sqlalchemy.orm import selectinload` to the imports
- Add `.options(selectinload(Product.order))` to the fetch query (line ~113)

**Rationale:** Without eager loading, each of the 50 rows in the product list would trigger a separate lazy-load query to fetch the parent Order's DATE and SUPPLIER. With `selectinload`, a single JOIN query fetches all data.

---

### 4. `App/main.qml` — Conditional View Rendering

**Current state:** Shows only `WelcomeScreen {}` inside a `RowLayout`. Has `selectedItem` and `selectedGroup` properties but no view switching.

**Changes needed:**

Replace the `WelcomeScreen {}` inside the `RowLayout` with a conditional:

```qml
RowLayout {
    anchors.top: menuBarContainer.bottom
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    spacing: 0

    ProductList {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: root.selectedItem === "Pedidos" && root.selectedGroup === "Notas"
    }

    WelcomeScreen {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: !(root.selectedItem === "Pedidos" && root.selectedGroup === "Notas")
    }
}
```

**Rationale:** Uses the existing `selectedItem` and `selectedGroup` properties set by `TopNavbar`'s `itemClicked` signal. When the user clicks **"Notas → Pedidos"** in the navigation, `selectedItem` becomes `"Pedidos"` and `selectedGroup` becomes `"Notas"`, making `ProductList` visible. All other selections show `WelcomeScreen`.

**Note:** The `visible` property is used (not `Loader` + `sourceComponent`) to avoid component recreation on every nav click. The `ProductList` component will be constructed at startup but won't render until visible.

---

### 5. `App/qmldir` — Register `ProductList` Component

**Current state:** Lists 7 components (Main, WelcomeScreen, NavigationGroup, NavItem, WelcomeIcon, TopNavbar, Constants).

**Changes needed:**

Add one line:

```
ProductList 1.0 ProductList.qml
```

**Rationale:** The QML module system requires all components to be declared in `qmldir` before they can be imported.

---

## Data Model Changes

### Product List Row Shape (after backend fix)

Each row returned by `BackendManager.product_list()` will have this shape:

```python
{
    "date": "2024-07-15",       # ISO format — model converts to "15/07/2024"
    "supplier": "Fornecedor X",  # Raw string
    "name": "Cimento CP-II",     # Raw string
    "price": 2599,               # Integer cents (R$ 25,99)
    "totalPrice": 129950,        # Integer cents (R$ 1.299,50)
    "orderId": "uuid-here",      # For future edit navigation
}
```

### Model Role Mapping

| Role | Qt.UserRole + N | QML Role Name | Data Transformation |
|------|----------------|---------------|---------------------|
| Date | 1 | `date` | `iso_to_br_date(raw)` → `"15/07/2024"` |
| Supplier | 2 | `supplier` | Raw string |
| Name | 3 | `name` | Raw string |
| Unit Price | 4 | `price` | `cents_to_display(raw)` → `"R$ 25,99"` |
| Total Price | 5 | `totalPrice` | `cents_to_display(raw)` → `"R$ 1.299,50"` |
| Order ID | 6 | `orderId` | Raw string (hidden) |

---

## UI/UX Changes

### `ProductList.qml` Layout Structure

```
Rectangle (color: Constants.contentBg, anchors.fill: parent)
└── ColumnLayout (anchors.fill: parent, anchors.margins: Constants.contentMargins, spacing: 20)
    ├── RowLayout (filter form)
    │   ├── ColumnLayout (supplier filter)
    │   │   ├── Text "Fornecedor"
    │   │   └── TextField { id: supplierField, placeholderText: "Fornecedor" }
    │   ├── ColumnLayout (product filter)
    │   │   ├── Text "Produto"
    │   │   └── TextField { id: productField, placeholderText: "Produto" }
    │   ├── ColumnLayout (month filter)
    │   │   ├── Text "Mês"
    │   │   └── TextField { id: monthField, placeholderText: "Mês", inputMask: "99/9999" }
    │   └── ColumnLayout (buttons)
    │       ├── Button { text: "Consultar", onClicked: onConsultar() }
    │       └── Button { text: "Limpar", onClicked: onLimpar() }
    ├── TableView (product data)
    │   ├── model: ProductListModel {}
    │   ├── horizontalScrollBarPolicy: ScrollBar.AsNeeded
    │   ├── verticalScrollBarPolicy: ScrollBar.AsNeeded
    │   └── 6 columns (TableViewColumn for each role)
    ├── Item { Layout.preferredHeight: 10 } (spacer)
    └── RowLayout (pagination)
        ├── Button { text: "←", onClicked: goToPage(currentPage - 1), enabled: currentPage > 1 }
        ├── Text { text: "Página " + currentPage + " de " + pageCount }
        └── Button { text: "→", onClicked: goToPage(currentPage + 1), enabled: currentPage < pageCount }
```

**Styling notes:**
- **Native Qt feel:** Use standard `TextField`, `Button`, `TableView`, `TableViewColumn` without custom `background` rectangles or custom colors. Let the OS theme handle the look.
- **Labels:** Plain `Text` elements above each `TextField`, using `Constants.metaTextColor` for a subdued look consistent with `WelcomeScreen.qml`.
- **Table headers:** Use `TableViewColumn` with `title` properties set to the column labels ("Data", "Fornecedor", "Produto", "Preço unitário", "Preço total").
- **Currency formatting:** The model's `data()` method returns the already-formatted `cents_to_display()` string (e.g., `"1.234,56"`). Display as-is — no additional formatting in QML.
- **Date formatting:** The model's `data()` method returns the already-formatted `iso_to_br_date()` string (e.g., `"15/07/2024"`). Display as-is.
- **Table column widths:** Use `role`-based column definitions. Allow the table to auto-size columns or set reasonable `role`-specific widths (e.g., "Data" ~90px, "Preço unitário" ~100px, "Preço total" ~110px, others flexible).

**Filter form behavior:**
- "Consultar" button: reads `supplierField.text`, `productField.text`, `monthField.text`, resets `currentPage` to 1, calls `model.refresh(1, supplier, product, month)`.
- "Limpar" button: clears all three text fields, resets `currentPage` to 1, calls `model.refresh(1, "", "", "")`.

**Pagination behavior:**
- "←" button: calls `model.refresh(currentPage - 1, supplier, product, month)` (persists current filters).
- "→" button: calls `model.refresh(currentPage + 1, supplier, product, month)`.
- Page indicator: `Text { text: "Página " + currentPage + " de " + pageCount }`.
- Buttons disabled at boundaries (page 1 and last page).

**Auto-query on mount:** The `ProductList` component should call `model.refresh(1, "", "", "")` in its `Component.onCompleted` handler to load page 1 with no filters on mount.

---

## Implementation Order

1. **`src/backend/repositories/order_repository.py`** — Add `selectinload(Product.order)` to `search_products`. This is the foundation — without it, the table would show N+1 queries and potentially fail.

2. **`src/backend/qml/qml_transformers.py`** — Add `product_list_item_to_dict()` and update `product_page_to_dict()` to use it. This ensures the backend returns `date` and `supplier` fields.

3. **`src/backend/qml/qml_models.py`** — Add `ProductListModel` class. This is the bridge between the backend data and the QML table.

4. **`App/ProductList.qml`** — Create the full view component. This is the main deliverable.

5. **`App/main.qml`** — Replace `WelcomeScreen {}` with conditional `ProductList` + `WelcomeScreen` (checking `selectedItem === "Pedidos" && selectedGroup === "Notas"`).

6. **`App/qmldir`** — Register `ProductList` component.

**Why this order:** Steps 1–2 fix the backend data gap. Step 3 creates the model that consumes the fixed data. Step 4 builds the UI on top of the model. Steps 5–6 wire everything together. No changes are needed to `Constants.qml` or `TopNavbar.qml` — the existing "Pedidos" nav item under "Notas" is reused as the navigation trigger. Each step can be verified independently.

---

## Verification Steps

### Run the app
```powershell
.\.venv\Scripts\Activate.ps1
python src/main.py
```

### Verify Product List view loads
1. Open the app.
2. Click **Notas → Pedidos** in the menu bar.
3. The Product List view should appear with:
   - Three empty filter fields ("Fornecedor", "Produto", "Mês")
   - A data table with 6 columns
   - Pagination controls at the bottom
   - Data from page 1 (up to 50 rows)

### Verify filters
1. Type a supplier name (e.g., part of an existing supplier) in the "Fornecedor" field.
2. Click "Consultar".
3. The table should refresh showing only matching products, page resets to 1.
4. Type a product name in the "Produto" field.
5. Click "Consultar" again.
6. Both filters should apply (AND logic).
7. Type a month in "MM/yyyy" format (e.g., "07/2024") using the mask `99/9999`.
8. Click "Consultar".
9. Results should be limited to products from orders in that month.
10. Click "Limpar" — all filters clear, table reloads page 1 with no filters.

### Verify pagination
1. If there are more than 50 products, the "→" button should be enabled.
2. Click "→" — table shows page 2, page indicator updates.
3. Click "←" — returns to page 1.
4. Filters should persist across page changes.

### QML linting
```powershell
.\.venv\Scripts\Activate.ps1
& ".venv\Lib\site-packages\PySide6\qmllint.exe" -I . App\ProductList.qml
```

---

## Risks and Considerations

### 1. N+1 Query Problem (CRITICAL)
The `search_products` query does not eagerly load `Product.order`. Without `selectinload(Product.order)`, each of the 50 rows triggers a separate SQL query to fetch the parent Order. This is a **significant performance regression** for the first view users will interact with. The `selectinload` fix in step 1 is mandatory.

### 2. Currency Formatting Consistency
The existing `cents_to_display()` utility returns strings like `"1.234,56"` (Brazilian format). The Product List view should display these directly in the table cells. However, the documentation says `R$ X,XX` format. Decide whether to prefix with "R$ " in the model's `data()` method or rely on the table column header. **Recommendation:** Display raw `cents_to_display()` output (e.g., `"1.234,56"`) without the "R$ " prefix — the column header "Preço unitário" already provides the context. If the user insists on "R$ " prefix, add it in the model.

### 3. Table Model vs List Model
The existing `OrderListModel` and `ExpenseListModel` extend `QAbstractListModel`. `TableView` requires `QAbstractTableModel`. This is not a compatibility issue (they are different base classes), but it means the new `ProductListModel` cannot reuse the list-model pattern directly. The table model has `rowCount()` AND `columnCount()` and maps roles to columns rather than rows.

### 4. Component Visibility vs Loader
Using `visible` (rather than `Loader` with `sourceComponent`) means `ProductList` is constructed at startup even when not visible. This is acceptable for a single view but could become a concern if more views are added. The `ProductListModel` will be instantiated and its `refresh()` called in `Component.onCompleted`, which fires even when `visible: false`. This is fine — the model loads data in the background and the table simply won't render until the user navigates to the view.

### 5. Month Filter Input Mask
The `inputMask: "99/9999"` on the month `TextField` enforces the format but does NOT validate that the month is 01-12 or the year is reasonable. The backend `search_products` already validates this (raises `ValueError` for invalid month). The `BackendManager.product_list()` catches this and emits `error_occurred`, returning an empty result. This is acceptable UX — the user sees an empty table and can try again.

### 6. Table Column Ordering
The documentation specifies column order: Data, Fornecedor, Produto, Preço unitário, Preço total. The role names should map to these in order. The hidden `orderId` role should not appear as a visible column.

### 7. Scroll Behavior
`TableView` in Qt Quick Controls 2 supports `horizontalScrollBarPolicy` and `verticalScrollBarPolicy`. For a native feel, set both to `ScrollBar.AsNeeded`. If the table has many columns, horizontal scrolling should be enabled.

---

## Edge Cases

- **Empty database:** The table shows 0 rows with an empty body. Pagination shows "Página 1 de 0". Previous/Next buttons are disabled.
- **Filter with no results:** Same as empty database — 0 rows, page count 0.
- **Invalid month format:** Backend returns empty result. Table shows 0 rows.
- **Very long supplier/product names:** `TableViewColumn` should allow text wrapping or truncation. Consider setting `textElideMode: Text.ElideMiddle` for the "Produto" column to handle long names.
- **Single page of results:** Pagination buttons disabled, indicator shows "Página 1 de 1".
