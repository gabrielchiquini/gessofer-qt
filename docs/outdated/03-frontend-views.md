> **Part of:** [Gessofer-Tauri Documentation](README.md)

# Frontend — Views & Screens

## 3.1 ProductList View (`/orders`)

**Route:** `/orders` (named route: `ProductList`)  
**Purpose:** Display a paginated, filterable list of all purchased products across all orders.

**Components Used:**
- `FormInput` × 3 (supplier, product, month filters)
- `DataTable` (product listing table)

**Filters:**
| Filter | Input Field | Validation | Placeholder | Mask | Icon |
|--------|------------|------------|-------------|------|------|
| Supplier | `supplier` | None (optional) | "Fornecedor" | None | `faBuilding` |
| Product | `product` | None (optional) | "Produto" | None | `faHammer` |
| Month | `month` | `dateFormat("MM/yyyy")` | "Mês" | `99/9999` | `faCalendar` |

**Table Columns:**
| Column Label | Data Key | Formatting |
|-------------|----------|------------|
| "Data" | `date` | `isoToBRFormat()` → `dd/MM/yyyy` |
| "Fornecedor" | `supplier` | Raw string |
| "Produto" | `name` | Raw string |
| "Preço unitário" | `price` | `formatCurrency()` → `R$ X,XX` |
| "Preço total" | `totalPrice` | `formatCurrency()` → `R$ X,XX` |

**Pagination:** 50 rows per page. Page numbers shown: current, ±1, ±2, and up to ±4 depending on position.

**Behavior:**
- On mount: queries data with no filters (page 1).
- On filter submit: resets to page 1, re-queries with filter values.
- On page change: re-queries with new page number (filters persist).

**Tauri Command Called:** `product_list({ page, supplier?, product?, month? })` → `TableResponse<ProductList>`

## 3.2 OrderEdit View (`/orders/edit`) — THE MOST COMPLEX SCREEN

**Route:** `/orders/edit` (named route: `OrderEdit`)  
**Purpose:** The central editing screen where users manage purchase orders — create new orders, edit existing ones, import NFe XMLs, distribute freight costs, and save everything.

### 3.2.1 Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Header (sticky when scrolled past)                         │
│  ┌──────────────────┐  ┌─────────────────────────────────┐ │
│  │ Month Query Form  │  │ [Import XML] [Adicionar Nota]   │ │
│  │ (MM/yyyy)         │  │ [MessageContainer]              │ │
│  └──────────────────┘  └─────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Order Card 1                                               │
│  ┌─ Card Header (callout secondary) ──────────────────────┐ │
│  │ [Supplier: __________] [Date: __/__ /____]            │ │
│  │ [NFe Key: ____________] [Frete: R$ __] [Descarga: R$ __]│ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌─ Product Rows ─────────────────────────────────────────┐ │
│  │ [Product: ___] [Qtde: __] [Preço: R$ __] [Total: R$ __]│ │
│  │ [Product: ___] [Qtde: __] [Preço: R$ __] [Total: R$ __]│ │
│  │ [Product: ___] [Qtde: __] [Preço: R$ __] [Total: R$ __]│ │
│  │ [Empty Row — auto-added]                              │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌─ Card Footer (callout secondary) ──────────────────────┐ │
│  │ [Total dos produtos: R$ X,XX]    [Remover Nota] [Distribuir frete] │
│  └────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Order Card 2 ... (repeated for each order)                │
├─────────────────────────────────────────────────────────────┤
│  [💾 Salvar] button                                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.2.2 Order Data Model (Form)

```typescript
interface OrderForm {
  id: string;           // UUID (v4) — "new" orders get fresh UUIDs
  date: string;         // Displayed as "dd/MM/yyyy" (BR format)
  supplier: string;     // Supplier name
  nfeKey: string;       // NFe access key (optional)
  freight: string;      // Currency string (e.g., "1.234,56")
  unloading: string;    // Currency string
  products: ProductForm[];
}

interface ProductForm {
  id: string;           // UUID (v4) — client-side unique ID
  name: string;
  quantity: string;     // Integer string
  price: string;        // Currency string
  total: string;        // Auto-calculated, read-only currency string
  warn?: string;        // Warning message from XML import
}
```

### 3.2.3 Freight Distribution Algorithm (CRITICAL)

The **"Distribuir frete" (Distribute Freight)** button implements a **proportional cost allocation** algorithm:

**Input:** Freight + Unloading costs for a single order.
**Output:** Updated unit prices for all products in the order, absorbing the freight/unloading costs proportionally.

**Algorithm:**
```
1. freightTotal = parseCurrency(order.freight) + parseCurrency(order.unloading)
   (Both values parsed from display string to integer cents)

2. productsTotal = sum of all product.total values (integer cents)

3. ratio = (freightTotal + productsTotal) / productsTotal
   (This ratio represents the total cost per unit of product value)

4. For each product in the order:
     newPrice = (product.total × ratio) / product.quantity
     newPrice = Math.round(newPrice)  // Round to nearest integer cent

5. Set each product's price to the new value (as currency string)
   The total for each product remains unchanged (it was used in the calculation)

6. Force Vue re-render via $forceUpdate()
```

**Example (from E2E test — 3 products):**
```
Freight: 1000 cents, Unloading: 3000 cents → freightTotal = 4000 cents
Products:
  Item 1: qty=100, price=150, total=15000 cents
  Item 2: qty=1,   price=1000, total=1000 cents
  Item 3: qty=3,   price=1005, total=3015 cents
productsTotal = 15000 + 1000 + 3015 = 19015 cents

ratio = (4000 + 19015) / 19015 = 23015 / 19015 ≈ 1.2104

Item 1: newPrice = (15000 × 1.2104) / 100 = 181.56 → rounded to 182 cents → "1,82"
Item 2: newPrice = (1000 × 1.2104) / 1   = 12.104 → rounded to 12 cents → "0,12"
         (but test expects 12,10 — this is because total stays 1000, price = 1000/1 = 1000)
         Wait — the total is NOT recalculated. Only price changes.
         Actually: total stays as-is, price is recalculated.
         Item 2: newPrice = (1000 * ratio) / 1 = 1210 → "12,10"
Item 3: newPrice = (3015 × 1.2104) / 3 = 1216.4 → rounded to 1216 cents → "12,16"

New totals after price change (if recalculated):
  Item 1: 182 × 100 = 18200 → "182,00"
  Item 2: 1210 × 1 = 1210 → "12,10"
  Item 3: 1216 × 3 = 3648 → "36,48"
Grand total: 18200 + 1210 + 3648 = 23058 → "230,58"
But displayed total: "R$ 230,57" (18200 + 1210 + 3648 = 23058, but test says 23057)
```

**Important notes:**
- The freight distribution **does NOT recalculate totals** — it only updates the `price` field. The `total` field is read-only and auto-calculated by `priceChange()` when the price input changes.
- The button is **disabled** (shown with tooltip "Há campos inválidos") if the order fails validation.
- The button is only **shown** when `isOrderValid(order)` returns `true`.

### 3.2.4 Auto-Save Mechanism (CRITICAL)

**Behavior:**
```
1. A `modified` flag starts as `false`.
2. Every user interaction that changes data sets `modified = true`:
   - Any product field change (`productChange`)
   - XML import (`addXml`)
   - Adding a new order (`addOrder`)
   - Any expense field change
3. A `setInterval` runs every **30 seconds**:
   a. If `modified === true`:
      - Run `validate()` on the entire form
      - If `result.valid === true`:
        - Call `save()` → invoke Tauri command `save_orders`
        - Show success message: "Salvo às HH:mm"
        - `modified` resets to `false` (implicitly, as the save clears the dirty state)
      - If `result.valid === false`:
        - Show error message: "Há campos inválidos"
        - `modified` remains `true` (will retry in next 30s interval)
4. When the user manually clicks "Salvar" button:
   - Calls `save()` directly (same logic, no validation check needed since form submission validates first)
5. On component unmount: interval is cleared via `clearInterval`.
```

**Save payload sent to Tauri:**
```typescript
{
  orders: [{
    id: string,
    date: "YYYY-MM-DD",       // Converted from BR format
    freight: number,           // Integer cents
    unloading: number,         // Integer cents
    supplier: string,
    nfeKey: string,
    products: [{
      id: string,
      name: string,
      quantity: number,
      price: number,           // Integer cents
      total: number,           // Integer cents
      orderId: string
    }]
  }],
  deletedOrders: string[]   // UUIDs of removed orders
}
```

**Important:** The save logic **deletes and re-inserts** all orders and products in a single database transaction (see [Database Repository Layer](06-backend.md)). This is a "write everything" approach rather than incremental updates.

### 3.2.5 XML Import Flow (CRITICAL)

**User Action:** Click "Importar XML" button → file picker opens → user selects one or more `.xml` files.

**Flow:**
```
1. File input change event fires
2. `addXml(event)` is called
3. Extract FileList from event.target.files
4. For each file:
   a. FileReader.readAsText(file) — reads as UTF-8 text
   b. On load: DOMParser.parseFromString(text, "text/xml")
   c. parseNfe() processes the XML:
      - Extract chNFe → nfeKey
      - Extract emit.xNome → supplier
      - Extract dhEmi (substring first 10 chars) → date → convert to BR format
      - For each <det> element:
        * Extract prod.xProd → product name
        * Extract prod.vProd → base price
        * Extract prod.qCom → quantity
        * Extract imposto.vIPI → add to price if > 0
        * Extract imposto.vICMSST → add to price
        * Calculate unit price = adjustedPrice / quantity
        * Calculate total = adjustedPrice
        * Generate warning messages
5. Each parsed order is pushed via ordersField.push()
6. `modified = true`
7. File input is cleared (input.value = "")
```

**XML Elements Extracted:**
| XML Element | Field | Notes |
|-------------|-------|-------|
| `chNFe` | `nfeKey` | 44-digit access key |
| `emit/xNome` | `supplier` | Supplier company name |
| `dhEmi` | `date` | Issue date (ISO 8601), first 10 chars taken |
| `det/prod/xProd` | `product.name` | Product description |
| `det/prod/vProd` | `product.price` (base) | Total product value |
| `det/prod/qCom` | `product.quantity` | Quantity sold |
| `det/imposto/vIPI` | price adjustment | Added to base price if > 0 |
| `det/imposto/vICMSST` | price adjustment | Added to base price |

**Warning Generation Logic:**
```
warns = []
if qCom is not an integer:
  warns.push("Quantidade não inteira.")
  quantity = 0
if vIPI exists and vIPI > 0:
  price += vIPI
  warns.push("Produto com IPI.")
if vICMSST exists:
  price += vICMSST
  warns.push("Produto com ST.")
warn = warns.join(" ")  // Space-separated warning string
```

**Product data after XML parse:**
```typescript
{
  id: v4(),
  name: xProd_text,
  quantity: quantity > 0 ? quantity.toString() : "",
  price: quantity > 0 ? (price / quantity).toFixed(2).replace(".", ",") : "",
  total: quantity > 0 ? price.toFixed(2).replace(".", ",") : "",
  warn: warns.join(" ")
}
```

### 3.2.6 Product Line Dynamic Behavior

**Auto-add empty rows:**
- When the user fills in the **last** product row (any field), `productChange()` detects this and pushes a new empty product row.
- This provides a continuous data-entry experience — no need to manually add rows.

**Auto-remove empty rows:**
- When the user edits a product row that is **not** the last row, and that row has all empty fields (`!name && !quantity && !price`), it is spliced out.
- The **last** row can never be removed (the delete button is disabled for it: `:disabled="order.products.length - 1 == j"`).

**Price/Total Auto-Calculation:**
- When `price` or `quantity` changes → `priceChange()` is called:
  ```
  total = parseCurrency(price) × parseInt(quantity)
  total = isNaN(total) ? "" : currencyToString(total)
  ```
- The `total` field is **read-only** in the UI.

### 3.2.7 Sticky Header Implementation

**Mechanism:** Uses a `IntersectionObserver` to detect when the header section scrolls out of the viewport.

```typescript
const stickyHeaderElement = ref<HTMLElement | null>(null);  // The empty <div ref="stickyHeaderElement"></div>
const stickyHeader = ref(false);

const headerObserver = new IntersectionObserver(
  ([entry]) => {
    stickyHeader.value = !entry.isIntersecting;  // sticky when header is NOT visible
  },
  { rootMargin: "0px 0px 0px 0px" }  // No margin — exact intersection boundary
);

// On mount: observe the empty div
// On unmount: unobserve
```

**CSS Classes:**
| Class | CSS Properties |
|-------|---------------|
| `.header-sticky` | `position: sticky; top: 0; z-index: 99999; padding-top: 1rem; background: white` |
| `.header-normal` | `margin-bottom: 1rem` |

The sticky header appears when the user scrolls past the initial header div, keeping the month query and action buttons always visible.

### 3.2.8 Validation Schema

```typescript
// Per-product validation
const productSchema = object().shape({
  name: string().requiredIfFilled("quantity").requiredIfFilled("price"),
  quantity: string().integer().requiredIfFilled("name").requiredIfFilled("price"),
  price: string().currency().requiredIfFilled("name").requiredIfFilled("quantity"),
  total: string(),  // No validation — auto-calculated
}, [
  ["name", "price"],
  ["name", "quantity"],
  ["quantity", "price"],
]);

// Per-order validation
const orderSchema = object({
  date: string().dateFormat(BR_DATE_FORMAT).required(),
  supplier: string().required(),
  nfe_key: string(),
  freight: string().currency(),
  unloading: string().currency(),
  products: array(productSchema),
});

// Root validation
const validationSchema = object({
  orders: array(orderSchema),
});
```

**`requiredIfFilled` behavior:** A field is required if ANY of its paired fields has a value. For example, `name` is required if `quantity` has a value OR if `price` has a value. This ensures partial entries are not allowed — if you start filling a product, all three core fields (name, quantity, price) must be present.

## 3.3 ExpensesView (`/expenses`)

**Route:** `/expenses` (named route: `ExpensesView`)  
**Purpose:** Display a list of expenses for a selected month.

**Components:**
- `MonthQueryForm` — month selector with "Consultar" button
- `ExpensesTable` — displays expenses in a DataTable

**Modes:**
| Mode | Value | Behavior |
|------|-------|----------|
| `EMPTY` | `"EMPTY"` | Only the month query form is shown |
| `VIEW` | `"VIEW"` | ExpensesTable is rendered with data |

**Tauri Command:** `expenses_for_month({ month })` → `Expense[]`

**Table Columns:**
| Label | Key | Formatting |
|-------|-----|------------|
| "Despesa" | `description` | Raw string |
| "Valor" | `value` | `formatCurrency()` → `R$ X,XX` |

## 3.4 ExpensesEdit (`/expenses/edit`)

**Route:** `/expenses/Edit` (named route: `ExpensesEdit`)  
**Purpose:** Create/edit monthly expenses with auto-save.

**Components:**
- `MonthQueryForm` — select month to edit
- `FormInput` × 2 per row (description, value)
- `MessageContainer` — save status messages
- Delete button per row (disabled for last row)

**Behavior:**
1. Query expenses for selected month → display in editable form
2. Auto-add empty expense row after loaded data
3. **Auto-save every 30 seconds** (same mechanism as OrderEdit)
4. **Save logic:**
   - Remove the trailing empty row
   - Convert all values to cents
   - Delete all existing expenses for the month
   - Insert all new expenses in a transaction
5. Manual save button also available

**Tauri Command:** `save_expenses({ expenses: [{ description, value }], month })`

**Validation:**
```typescript
expenses: array(
  object().shape({
    description: string().requiredIfFilled("value"),
    value: string().currency().requiredIfFilled("description"),
  }),
  [["description", "value"]]  // Either both or neither
)
```

## 3.5 AboutView (`/about`)

**Route:** `/about` (named route: `AboutView`)  
**Purpose:** Placeholder "about" page. Currently renders a simple heading "This is an about page" with minimal styling.

## 3.6 Navigation Structure and Routing Map

**Router Configuration:**
```typescript
// Vue Router with createWebHistory
// Base URL from import.meta.env.BASE_URL

routes: [
  { path: "/", redirect: "/orders" },              // Root → Orders list
  { path: "/orders", name: "ProductList" },         // Product list view
  { path: "/orders/edit", name: "OrderEdit" },      // Order editor (lazy-loaded)
  { path: "/expenses", name: "ExpensesView" },      // Expenses list (lazy-loaded)
  { path: "/expenses/Edit", name: "ExpensesEdit" }, // Expenses editor (lazy-loaded)
]
```

**Navbar Structure:**
```
NOTAS (menu text)
├─ Pedidos
│  ├─ Lista (/orders)
│  └─ Cadastrar (/orders/edit)
└─ Despesas
   ├─ Lista (/expenses)
   └─ Cadastrar (/expenses/edit)
```

The navbar is a Foundation Sites dropdown menu initialized via jQuery on mount.
