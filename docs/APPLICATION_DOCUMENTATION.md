# Gessofer-Tauri — Application Documentation

> **Purpose:** This document provides a complete, exhaustive specification of the Gessofer-Tauri application, enabling developers to implement a full rewrite in Python + PySide6 without needing to reference the original source code.

> **Version:** Current application version is `0.0.0`. Built with Tauri 2 (beta), Vue 3, TypeScript, and SQLite via SeaORM.

---

## Table of Contents

1. [Application Overview & Business Context](#1-application-overview--business-context)
2. [Database Schema & Data Model](#2-database-schema--data-model)
3. [Frontend — Views & Screens](#3-frontend--views--screens)
4. [Frontend — Components](#4-frontend--components)
5. [Frontend — Utilities & Shared Logic](#5-frontend--utilities--shared-logic)
6. [Backend — Rust/Tauri Architecture](#6-backend--rusttauri-architecture)
7. [Styling & UI Framework](#7-styling--ui-framework)
8. [Build & Deployment](#8-build--deployment)
9. [Testing](#9-testing)
10. [Migration Mapping (for Python Port)](#10-migration-mapping-for-python-port)

---

## 1. Application Overview & Business Context

### 1.1 High-Level Purpose

Gessofer-Tauri is a **purchasing and order management desktop application** for **Gessofer**, a Brazilian building materials supplier (likely specializing in gypsum/plaster products, given the name "Gessofer"). The application manages:

- **Purchase orders (Notas Fiscais / NFe):** Recording incoming supplier invoices with line-item products, prices, freight (transportation) costs, and unloading costs.
- **Product price tracking:** A searchable, filterable, paginated list of all products purchased across orders.
- **Operating expenses (Despesas):** Monthly expense tracking for business overhead.
- **NFe XML import:** Automatic parsing of Brazilian electronic invoice XML files to pre-populate order data.

The application runs as a **desktop app** using Tauri (Rust backend + web frontend), packaged as a Windows installer via WiX.

### 1.2 User Roles and Target Users

| Role | Description |
|------|-------------|
| **Purchase Manager / Buyer** | Primary user. Creates/edit purchase orders, imports NFe XMLs, distributes freight costs across products, and tracks expenses. |
| **Administrator** | Manages the database, runs migrations, and oversees the application. |

There is **no authentication system** — the application assumes a single trusted user operating locally on a Windows machine.

### 1.3 Glossary of Brazilian Business Terms

| Term | English Equivalent | Description |
|------|--------------------|-------------|
| **NFe (Nota Fiscal Eletrônica)** | Electronic Invoice | Brazil's official electronic invoice document for commercial transactions. Contains product details, taxes (IPI, ICMS-ST), supplier info, and a unique access key (chNFe). |
| **frete** | Freight / Transportation | Cost of transporting goods from supplier to the business. |
| **descarga** | Unloading | Cost of unloading goods upon arrival. |
| **ST (Substituição Tributária)** | Tax Substitution | A Brazilian tax mechanism where the supplier collects ICMS tax on behalf of the buyer for future transactions. |
| **IPI (Imposto sobre Produtos Industrializados)** | Tax on Industrialized Products | Federal tax levied on manufactured goods. |
| **nota fiscal** | Invoice / Receipt | The fiscal document recording a transaction. |
| **fornecedor** | Supplier / Vendor | The company selling materials to Gessofer. |
| **chNFe** | NFe Access Key | A 44-digit unique identifier for each NFe. |
| **xNome** | Company Name | The legal name of the supplier extracted from the NFe XML. |
| **vProd** | Product Value | The total value of a product line item in the NFe. |
| **qCom** | Quantity Sold | The quantity of units sold in a product line item. |
| **vIPI** | IPI Tax Value | The IPI tax amount for a product. |
| **vICMSST** | ICMS-ST Tax Value | The ICMS substitution tax amount for a product. |
| **despesa** | Expense | Business overhead cost (rent, utilities, etc.). |

### 1.4 Data Currency Format Convention

All monetary values are stored in the database as **integer cents** (32-bit signed integers), NOT as floating-point decimals.

| Display Format (UI) | Stored Format (DB) | Conversion |
|---------------------|--------------------|------------|
| `R$ 1.234,56` | `123456` | Display: divide by 100, format with Brazilian locale (`.` as thousands separator, `,` as decimal separator) |
| `R$ 0,99` | `99` | Parse: remove formatting, replace `,` with `.`, multiply by 100, floor to integer |

**Conversion functions:**

- **To display string:** `"R$ " + integer.toString().split into integer part (thousands separated by `.`) and decimal part (2 digits, comma-separated)`
- **To integer cents:** `parseFloat(string.replace(",", ".")) * 100 | 0` (floor)

**Example:**
```
Display: "R$ 1.234,56"  →  DB: 123456
Display: "R$ 0,99"      →  DB: 99
Display: "R$ 10.000,00" →  DB: 1000000
```

---

## 2. Database Schema & Data Model

### 2.1 Complete Current SQLite Schema (New Schema)

The application uses **three tables** in the current database (`main.db`).

#### Table: `ORDER`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `ID` | TEXT (VARCHAR) | PRIMARY KEY, NOT NULL, auto_increment=false | UUID string identifier |
| `DATE` | DATE | NOT NULL | Purchase date (YYYY-MM-DD) |
| `SUPPLIER` | TEXT | NOT NULL | Supplier's display name (with Portuguese characters) |
| `SUPPLIER_NORMALIZED` | TEXT | NOT NULL | ASCII-normalized supplier name (for case-insensitive/fuzzy search) |
| `NFE_KEY` | TEXT | NULLABLE | 44-digit NFe access key |
| `FREIGHT` | INTEGER | NOT NULL | Freight cost in cents |
| `UNLOADING` | INTEGER | NOT NULL | Unloading cost in cents |
| `CREATED_AT` | DATETIME | NOT NULL | Row creation timestamp |
| `UPDATED_AT` | DATETIME | NOT NULL | Last update timestamp |

#### Table: `PRODUCT`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `ID` | TEXT (VARCHAR) | PRIMARY KEY, NOT NULL, auto_increment=false | UUID string identifier |
| `NAME` | TEXT | NOT NULL | Product name (with Portuguese characters) |
| `NAME_NORMALIZED` | TEXT | NOT NULL | ASCII-normalized product name (for search) |
| `QUANTITY` | INTEGER | NOT NULL | Quantity of units purchased |
| `PRICE` | INTEGER | NOT NULL | Unit price in cents |
| `TOTAL_PRICE` | INTEGER | NOT NULL | Total line item price (quantity × price) in cents |
| `ORDER_ID` | TEXT | NOT NULL, FOREIGN KEY → ORDER.ID | Parent order reference |
| `ITEM_ORDINAL` | INTEGER | NULLABLE | Line item position within the order (0-indexed) |
| `CREATED_AT` | DATETIME | NOT NULL | Row creation timestamp |
| `UPDATED_AT` | DATETIME | NOT NULL | Last update timestamp |

#### Table: `EXPENSE`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `ID` | INTEGER | PRIMARY KEY, auto_increment | Auto-incrementing integer ID |
| `MONTH` | TEXT | NOT NULL | Month in `YYYY-MM` format |
| `DESCRIPTION` | TEXT | NOT NULL | Expense description |
| `VALUE` | INTEGER | NOT NULL | Expense amount in cents |
| `CREATED_AT` | DATETIME | NOT NULL | Row creation timestamp |
| `UPDATED_AT` | DATETIME | NOT NULL | Last update timestamp |

### 2.2 Legacy Database Schema (Old Tables)

The migration tool (`migrate.rs`) reads from a legacy database file (`main-2025-12.db`) with these tables:

#### Table: `NOTA` (Invoice)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NOT NULL | Auto-increment primary key |
| `data` | DATETIME | YES | Invoice date |
| `fornecedor` | TEXT | YES | Supplier name |
| `chaveNFE` | TEXT | YES | NFe access key |
| `frete` | DOUBLE | YES | Freight cost (float) |
| `descarga` | DOUBLE | YES | Unloading cost (float) |
| `createdAt` | DATETIME | NOT NULL | Creation timestamp |
| `updatedAt` | DATETIME | NOT NULL | Update timestamp |

#### Table: `PRODUTOS` (Products)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NOT NULL | Auto-increment primary key |
| `nome` | TEXT | YES | Product name |
| `quantidade` | DOUBLE | YES | Quantity (can be fractional) |
| `precoUnitario` | DOUBLE | YES | Unit price (float) |
| `precoTotal` | DOUBLE | YES | Total price (float) |
| `fkNota` | INTEGER | YES | Foreign key → NOTA.id |
| `createdAt` | DATETIME | NOT NULL | Creation timestamp |
| `updatedAt` | DATETIME | NOT NULL | Update timestamp |

#### Table: `EXPENSES` (Expenses)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NOT NULL | Auto-increment primary key |
| `name` | TEXT | YES | Expense name/description |
| `value` | DOUBLE | YES | Expense value (float) |
| `month` | DOUBLE | YES | Month number (1-12) |
| `year` | DOUBLE | YES | Year |
| `createdAt` | DATETIME | NOT NULL | Creation timestamp |
| `updatedAt` | DATETIME | NOT NULL | Update timestamp |

### 2.3 Entity Relationships

```
┌──────────────┐       ┌──────────────────┐
│    ORDER     │ 1───┐ │     PRODUCT      │
├──────────────┤     │ ├──────────────────┤
│ ID (PK)      │     │ │ ID (PK)          │
│ DATE         │     │ │ NAME             │
│ SUPPLIER     │     │ │ NAME_NORMALIZED  │
│ NFE_KEY      │     │ │ QUANTITY         │
│ FREIGHT      │     │ │ PRICE            │
│ UNLOADING    │     │ │ TOTAL_PRICE      │
│ CREATED_AT   │     │ │ ORDER_ID (FK)    │──→ ORDER.ID
│ UPDATED_AT   │     │ │ ITEM_ORDINAL     │
└──────────────┘     │ └──────────────────┘
                     │
                     │
┌──────────────┐     │
│   EXPENSE    │     │
├──────────────┤     │
│ ID (PK, AI)  │     │
│ MONTH        │     │
│ DESCRIPTION  │     │
│ VALUE        │     │
│ CREATED_AT   │     │
│ UPDATED_AT   │     │
└──────────────┘     │
```

- **ORDER 1──N PRODUCT:** Each order has one or more product line items.
- **EXPENSE is standalone:** No foreign key relationships.

### 2.4 Data Migration Strategy

The `migrate.rs` binary performs a one-time migration from the legacy database to the new schema:

1. **Open the new database** (via `DATABASE_URL` env var or default path).
2. **Begin a transaction.**
3. **Truncate** all three new tables (`EXPENSE`, `PRODUCT`, `ORDER`).
4. **Open the legacy database** (`./main-2025-12.db`).
5. **For each legacy table:**
   - **EXPENSES → EXPENSE:**
     - `id` → `id` (direct copy)
     - `year` + `month` → `month` (formatted as `"YYYY-MM"`)
     - `name` → `description`
     - `value` (float) → `value` (int cents): `value * 100`
     - `createdAt` → `created_at`, `updatedAt` → `updated_at`
   - **NOTA → ORDER:**
     - `id` → `id` (converted to string)
     - `data` → `date` (Date only)
     - `fornecedor` → `supplier` (direct) + `SUPPLIER_NORMALIZED` (ASCII-normalized via `unidecode`)
     - `chaveNFE` → `nfe_key`
     - `frete` (float) → `freight` (int cents): `frete * 100`
     - `descarga` (float) → `unloading` (int cents): `descarga * 100`
   - **PRODUTOS → PRODUCT:**
     - `id` → `id` (converted to string)
     - `nome` → `name` (direct) + `NAME_NORMALIZED` (ASCII-normalized via `unidecode`)
     - `quantidade` → `quantity` (float → int)
     - `precoUnitario` (float) → `price` (int cents): `preco * 100`
     - `precoTotal` (float) → `total_price` (int cents): `preco * 100`
     - `fkNota` → `order_id`
6. **Commit transaction.**

### 2.5 Database File Locations and Discovery Logic

The application discovers the database file using this priority order:

| Environment | Discovery Method | Default Path |
|-------------|-----------------|--------------|
| **Development** (`DATABASE_URL` env var set) | Uses the connection string from the env var | User-specified |
| **Production (Windows)** | Reads `LOCALAPPDATA` env var → `C:\Users\<User>\AppData\Local\gessofer-tauri\main.db` | `%LOCALAPPDATA%\gessofer-tauri\main.db` |
| **E2E Tests** | Reads `TEMP` env var → `%TEMP%\tmp-gessofer-tauri.db` | `%TEMP%\tmp-gessofer-tauri.db` |

**Discovery code flow:**
```
1. Try env::var("DATABASE_URL")
   └─ If Ok → use that URL
   └─ If Err → try default path:
       a. Check if %LOCALAPPDATA%\gessofer-tauri\main.db exists
          └─ If yes → use it
          └─ If no → return error "Nenhum arquivo de banco encontrado"
```

### 2.6 Field Naming Conventions

| Context | Convention | Examples |
|---------|-----------|----------|
| **Database columns** | UPPERCASE_SNAKE_CASE | `SUPPLIER`, `NFE_KEY`, `TOTAL_PRICE` |
| **Rust struct fields** | snake_case | `supplier`, `nfe_key`, `total_price` |
| **JSON API fields** | camelCase | `supplier`, `nfeKey`, `totalPrice` |
| **Vue/TypeScript model fields** | camelCase | `supplier`, `nfeKey`, `totalPrice` |
| **Normalized fields** | `*_normalized` suffix | `supplier_normalized`, `name_normalized` |

---

## 3. Frontend — Views & Screens

### 3.1 ProductList View (`/orders`)

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

### 3.2 OrderEdit View (`/orders/edit`) — THE MOST COMPLEX SCREEN

**Route:** `/orders/edit` (named route: `OrderEdit`)  
**Purpose:** The central editing screen where users manage purchase orders — create new orders, edit existing ones, import NFe XMLs, distribute freight costs, and save everything.

#### 3.2.1 Layout Structure

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

#### 3.2.2 Order Data Model (Form)

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

#### 3.2.3 Freight Distribution Algorithm (CRITICAL)

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

#### 3.2.4 Auto-Save Mechanism (CRITICAL)

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

**Important:** The save logic **deletes and re-inserts** all orders and products in a single database transaction (see Backend section). This is a "write everything" approach rather than incremental updates.

#### 3.2.5 XML Import Flow (CRITICAL)

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

#### 3.2.6 Product Line Dynamic Behavior

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

#### 3.2.7 Sticky Header Implementation

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

#### 3.2.8 Validation Schema

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

### 3.3 ExpensesView (`/expenses`)

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

### 3.4 ExpensesEdit (`/expenses/edit`)

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

### 3.5 AboutView (`/about`)

**Route:** `/about` (named route: `AboutView`)  
**Purpose:** Placeholder "about" page. Currently renders a simple heading "This is an about page" with minimal styling.

### 3.6 Navigation Structure and Routing Map

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

---

## 4. Frontend — Components

### 4.1 AppNavbar

**File:** `src/components/AppNavbar.vue`

**Purpose:** Top navigation bar with dropdown menus for Orders and Expenses sections.

**Behavior:**
- Initializes Foundation dropdown menu on mount: `$("#navbar").foundation()`
- Destroys on unmount: `$("#navbar").foundation("destroy")`
- Uses jQuery for Foundation initialization (Foundation Sites dependency)

**Structure:**
- `<div class="top-bar">` → Foundation top-bar container
- `<div class="top-bar-left">` → Left-aligned content
- `<ul class="dropdown menu" id="navbar" data-dropdown-menu>` → Foundation dropdown menu
- `<hr class="navbar-divider">` → Visual separator below navbar

**Key IDs for E2E testing:**
| ID | Element |
|----|---------|
| `#navbar` | Menu container |
| `#nav-menu-orders` | Pedidos dropdown trigger |
| `#nav-link-orders-list` | Lista link |
| `#nav-link-orders-create` | Cadastrar link |

### 4.2 DataTable

**File:** `src/components/DataTable.vue`

**Purpose:** Generic paginated data table with slot-based column rendering.

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `fields` | `FieldDefinition[]` | Required | Column definitions: `{ label?, key }` |
| `rows` | `Record<string, any>[]` | Required | Data rows |
| `pageCount` | `number` | Optional | Total number of pages |
| `page` | `number` | Optional | Current page number |

**Events:**
| Event | Payload | Description |
|-------|---------|-------------|
| `pageChanged` | `number` (new page) | Emitted on pagination button click |

**Slots:**
| Slot Name | Props | Description |
|-----------|-------|-------------|
| `row:{key}` | `{ row }` | Custom rendering for a specific column |

**Pagination:** Foundation Sites pagination component with:
- First page button (double left arrow)
- Previous page button (single left arrow, disabled on page 1)
- Page number links (up to 2 pages before/after current)
- Current page indicator
- Next page button (single right arrow, disabled on last page)
- Last page button (double right arrow)

### 4.3 FormInput

**File:** `src/components/FormInput.vue`

**Purpose:** Reusable form input with label, optional icon, input masking, and vee-validate integration.

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `name` | `string` | Required | Field name for vee-validate |
| `modelValue` | `string` | `""` | Two-way bound value |
| `inputName` | `string` | `name` | HTML `name` attribute |
| `label` | `string` | `""` | Label text |
| `placeholder` | `string` | `""` | Input placeholder |
| `iconLeft` | `IconDefinition` | `null` | FontAwesome icon for left input group |
| `mask` | `string` | `null` | Inputmask mask pattern (e.g., `99/9999`) |
| `controlExtraClass` | `string` | `""` | Additional CSS classes |
| `expanded` | `boolean` | `false` | Makes input take full width |
| `readonly` | `boolean` | `false` | Read-only input |
| `id` | `string` | auto-generated | Input ID (uses `uniqueId()` if not provided) |

**Slots:**
| Slot | Description |
|------|-------------|
| `input-group-button` | Right-side button(s) in the input group |

**Integration:**
- Uses `useField()` from vee-validate for validation state
- Displays `form-error` with `is-visible` class when validation fails
- Applies `is-invalid-input` class to the input when invalid
- Uses Inputmask library for mask patterns (initialized on mount)

**Foundation Structure:**
```html
<label> → <div class="control input-group [expanded]">
  <span class="input-group-label"> (icon)
  <input class="input-group-field [is-invalid-input]">
  <div class="input-group-button"> (slot)
</div>
<span class="form-error [is-visible]"> (error message)
```

### 4.4 MonthQueryForm

**File:** `src/components/MonthQueryForm.vue`

**Purpose:** Month selector input with "Consultar" (Query) button.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `initialValue` | `string` | Pre-filled month value (e.g., "07/2024") |

**Events:**
| Event | Payload | Description |
|-------|---------|-------------|
| `query` | `string` (month) | Emitted when form is submitted |

**Validation:**
- Month field: `dateFormat("MM/yyyy")` required
- Mask: `99/9999`

**Structure:** Single `FormInput` with a button in the `input-group-button` slot.

### 4.5 AlertContainer

**File:** `src/components/AlertContainer.vue`

**Purpose:** Displays global alerts from the Pinia `alert` store.

**Source:** `useAlertStore()` from `src/stores/alert.ts`

**Appearance:**
- Position: absolute, top: 80px, right: 20px
- Minimum width: 300px
- Uses Foundation callout classes: `.callout .alert-absolute [type]`
- Type classes: `primary`, `secondary`, `success`, `warning`, `alert`

**Animation:** Vue `<Transition>` with:
- Enter: 0.5s ease-out, translateX(80px) → 0
- Leave: 0.8s cubic-bezier(1, 0.5, 0.8, 1), 0 → translateX(80px)

**Auto-hide:** Alerts auto-hide after 10 seconds via `setTimeout` in the store.

### 4.6 MessageContainer

**File:** `src/components/MessageContainer.vue`

**Purpose:** Displays success/error messages (used by OrderEdit and ExpensesEdit for save feedback).

**Type:** `"success" | "error"`

**API:**
```typescript
// Exposed via defineExpose
function setMessage(message: string, type: MessageType): void
```

**Appearance:**
- Success: `<span class="success label">` with check icon (`faCheck`)
- Error: `<span class="alert label">` with close icon (`faClose`)

**Behavior:** Only one message shown at a time (clears the other type when setting a new message).

### 4.7 FoundationTooltip

**File:** `src/components/FoundationTooltip.vue`

**Purpose:** Wrapper around Foundation Sites Tooltip for displaying hover/click tooltips.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `text` | `string` | Tooltip text content |

**Implementation:**
- Uses Foundation Sites `new Tooltip(element)` on mount
- Wraps content in a `<span>` with `title` attribute
- Uses jQuery for Foundation initialization

**Usage Pattern:**
```vue
<FoundationTooltip text="Há campos inválidos">
  <button disabled>Distribuir frete</button>
</FoundationTooltip>
```

### 4.8 ExpensesTable

**File:** `src/components/ExpensesTable.vue`

**Purpose:** Specialized DataTable for displaying expenses.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `expenses` | `Expense[]` | Array of expense objects |

**Columns (hardcoded):**
| Label | Key | Formatting |
|-------|-----|------------|
| "Despesa" | `description` | Raw |
| "Valor" | `value` | `formatCurrency()` |

**Delegation:** Simply wraps `DataTable` with pre-configured fields and a slot for currency formatting.

---

## 5. Frontend — Utilities & Shared Logic

### 5.1 Date Utilities

**File:** `src/util/date.ts`

**Library:** Luxon (`DateTime`)

**Format Constants:**
| Constant | Value | Example |
|----------|-------|---------|
| `ISO_DATE_FORMAT` | `"yyyy-MM-dd"` | `"2024-07-24"` |
| `BR_DATE_FORMAT` | `"dd/MM/yyyy"` | `"24/07/2024"` |
| `BR_TIME_FORMAT` | `"HH:mm"` | `"14:30"` |
| `MONTH_DATE_FORMAT` | `"MM/yyyy"` | `"07/2024"` |

**Functions:**
| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `isoToBRFormat(date: string)` | `"2024-07-24"` | `"24/07/2024"` | Convert ISO date to Brazilian format |
| `BRToIsoFormat(date: string)` | `"24/07/2024"` | `"2024-07-24"` | Convert Brazilian date to ISO format |
| `parseIsoDate(date: string)` | `"2024-07-24"` | `DateTime` | Parse ISO date to Luxon DateTime |
| `formatDateBR(date: DateTime)` | `DateTime` | `"24/07/2024"` | Format DateTime to Brazilian date |
| `formatMonthBR(date: DateTime)` | `DateTime` | `"07/2024"` | Format DateTime to month/year |
| `parseDateBR(dateString: string)` | `"24/07/2024"` | `DateTime` | Parse Brazilian date to Luxon DateTime |

### 5.2 Currency Utilities

**File:** `src/util/currency.ts`

**Core Convention:** All monetary values stored as **integer cents**.

**Functions:**
| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `formatCurrency(value: number)` | `123456` | `"R$ 1.234,56"` | Format cents to Brazilian currency string with "R$ " prefix |
| `currencyToString(value: number)` | `123456` | `"1.234,56"` | Format cents to Brazilian currency string (no "R$ ") |
| `parseCurrency(value: string)` | `"1.234,56"` | `123456` | Parse currency string to integer cents |

**Implementation Details:**
```
currencyToString:
  mod = value % 100          // Decimal part
  integer = floor(value / 100)  // Integer part
  return "${integer},${pad(mod, 2)}"
  Note: The current implementation does NOT add thousands separators (dots).
  It simply returns the integer part as-is followed by comma and 2-digit decimal.

parseCurrency:
  if (!value) return 0
  valueFloat = parseFloat(value.replace(",", ".")) * 100
  return floor(valueFloat)
```

**Note:** The `currencyToString` function does NOT add thousands separators. The format is `${integer},${decimal}` without dots for thousands. The E2E test expects `"3.42"` for value 342, which suggests the display uses `/` or `.` differently. Review actual test expectations carefully.

### 5.3 Validation Extensions

**File:** `src/util/validation.ts`

**Library:** Yup (with vee-validate integration)

**Locale Configuration:**
```typescript
setLocale({
  mixed: {
    required: "Campo obrigátorio"  // Note: typo in original ("obrigatóriO" → "obrigatóriO")
  }
});
```

**Custom String Methods:**

| Method | Parameters | Validation | Error Message |
|--------|-----------|------------|---------------|
| `dateFormat(format)` | `format: string` | Checks if value parses correctly with Luxon using the given format | "Data inválida" |
| `currency()` | none | Matches regex `/^\d+([.,]\d+)?$/` | "Valor inválido" |
| `integer()` | none | Matches regex `/^[0-9]*$/` | "Valor inválido" |
| `requiredIfFilled(field)` | `field: string` | Required if the sibling field has a value | "Campo obrigátorio" |

**Regex Patterns:**
- Currency: `/^\d+([.,]\d+)?$/` — allows digits with optional decimal separator (comma or period)
- Integer: `/^[0-9]*$/` — only digits, empty string is valid

**`requiredIfFilled` Logic:**
```typescript
addMethod(string, "requiredIfFilled", function (field) {
  return this.when(field, {
    is: (value) => !!value,
    then: (schema) => schema.required(),
  });
});
```
This uses Yup's cross-field dependency: the field becomes required when the specified sibling field has a truthy value.

### 5.4 NFe XML Parser

**File:** `src/util/parseNfe.ts`

**Purpose:** Parses Brazilian NFe (Nota Fiscal Eletrônica) XML files to extract order and product data.

**Function Signature:**
```typescript
function parseNfe(fileList: FileList): Promise<OrderForm[]>
```

**Full Parsing Logic:**

1. **File Processing:** Iterates over all files in the FileList. Each file is read asynchronously via `FileReader.readAsText()`.

2. **XML Parsing:** When a file loads:
   ```typescript
   const dom = new DOMParser().parseFromString(text, "text/xml").documentElement;
   ```

3. **Order-Level Extraction:**
   | XML Path | Field | Transformation |
   |----------|-------|---------------|
   | `chNFe` (first element) | `nfeKey` | Direct text content |
   | `emit/xNome` (first element) | `supplier` | Direct text content |
   | `dhEmi` (first element, chars 0-10) | `date` | ISO date → `isoToBRFormat()` → `"dd/MM/yyyy"` |

4. **Product-Level Extraction (per `<det>` element):**
   ```
   For each <det>:
     prod = <det/prod>
     imposto = <det/imposto>
     
     basePrice = parseFloat(<prod/vProd>)
     quantity = parseFloat(<prod/qCom>)
     
     warns = []
     
     // Warning: non-integer quantity
     if !Number.isInteger(quantity):
       warns.push("Quantidade não inteira.")
       quantity = 0
     
     // IPI adjustment
     if <imposto/vIPI> exists:
       ipiValue = parseFloat(<imposto/vIPI>.textContent)
       if !isNaN(ipiValue) && ipiValue > 0:
         basePrice += ipiValue
         warns.push("Produto com IPI.")
     
     // ICMS-ST adjustment
     if <imposto/vICMSST> exists:
       icmsStValue = parseFloat(<imposto/vICMSST>.textContent)
       basePrice += icmsStValue
       warns.push("Produto com ST.")
     
     // Final calculations
     unitPrice = basePrice / quantity  (if quantity > 0)
     totalPrice = basePrice             (if quantity > 0)
     
     // Format to Brazilian currency
     priceString = unitPrice.toFixed(2).replace(".", ",")
     totalString = totalPrice.toFixed(2).replace(".", ",")
     
     ProductForm = {
       id: v4(),
       name: <prod/xProd>.textContent,
       quantity: quantity > 0 ? quantity.toString() : "",
       price: quantity > 0 ? priceString : "",
       total: quantity > 0 ? totalString : "",
       warn: warns.join(" ")
     }
     Add to product list
   ```

5. **Post-Processing:**
   - An empty product row is appended to each order's product list (for user entry)
   - All orders are collected and resolved as a Promise

6. **Completion:** Resolves the Promise when all files have been processed (tracked via `processedCount` counter).

**XML Helper Function:**
```typescript
function getXMLText(tag: HTMLCollectionOf<Element>): string {
  if (tag.length) return tag[0].textContent ?? "";
  return "";
}
```

### 5.5 ID Generator

**File:** `src/util/ids.ts`

**Purpose:** Generates simple sequential string IDs for DOM elements.

```typescript
export const uniqueId = (() => {
  let i = 0;
  return () => {
    return "id-" + i++;
  };
})();
```

**Output:** `"id-0"`, `"id-1"`, `"id-2"`, ...

**Usage:** Only used by `FormInput` component to generate unique `id` attributes for accessibility (label-for association).

### 5.6 State Management

**File:** `src/stores/alert.ts`

**Library:** Pinia

**Store Definition:**
```typescript
export const useAlertStore = defineStore("alert", () => {
  const text = ref("");
  const display = ref(false);
  const type: Ref<alertType> = ref("primary");
  
  function showAlert(newType: alertType, newText: string) {
    text.value = newText;
    type.value = newType;
    display.value = true;
    setTimeout(() => hideAlert(), 10_000);  // Auto-hide after 10 seconds
  }
  
  function hideAlert() {
    display.value = false;
  }
  
  return { text, type, display, showAlert, hideAlert };
});
```

**Alert Types:** `"primary" | "secondary" | "success" | "warning" | "alert"`

**Note:** The alert store is defined but the `showAlert` function is never called from any view in the current codebase. The `AlertContainer` component renders but the store's `display` is always `false` unless `showAlert()` is called externally.

**Other State Management:**
- OrderEdit and ExpensesEdit use **local reactive state** (`ref`, `reactive`) rather than Pinia stores.
- The `modified` flag, `intervalRef`, `deletedOrders`, and `messageContainer` are all component-local.
- `useFieldArray` from vee-validate manages the dynamic product/expense arrays.

---

## 6. Backend — Rust/Tauri Architecture

### 6.1 Tauri 2 App Structure

```
src-tauri/
├── Cargo.toml              # Rust dependencies
├── tauri.conf.json         # Tauri app configuration
├── build.rs                # Build script (calls tauri_build::build())
├── capabilities/
│   └── migrated.json       # Migrated permissions from Tauri v1
├── src/
│   ├── main.rs             # Entry point (Windows GUI app)
│   ├── lib.rs              # Library root (exports AppData, modules)
│   ├── migrate.rs          # One-time database migration binary
│   ├── api/                # Tauri command handlers
│   │   ├── mod.rs
│   │   ├── orders_for_month.rs
│   │   ├── product_list.rs
│   │   ├── save_orders.rs
│   │   ├── save_expenses.rs
│   │   └── util.rs
│   ├── database/           # Database layer
│   │   ├── mod.rs
│   │   ├── connect.rs
│   │   ├── entity/         # SeaORM entity definitions
│   │   ├── entity_old/     # Legacy SeaORM entities
│   │   ├── expense_repository.rs
│   │   ├── order_repository.rs
│   │   └── product_repository.rs
│   ├── error/
│   │   └── mod.rs
│   └── model/              # API model structs
│       ├── mod.rs
│       ├── expense.rs
│       ├── order.rs
│       ├── page_response.rs
│       └── product_list.rs
├── migrations/
│   └── .keep               # (empty — migrations are manual)
└── icons/                  # App icons for packaging
```

### 6.2 Tauri Commands API Surface

**All 5 Commands:**

| Command Name | Parameters | Return Type | Description |
|-------------|-----------|-------------|-------------|
| `orders_for_month` | `month: String` | `Result<Vec<Order>>` | Fetches all orders for a given month (MM/yyyy format). Returns orders with their products. |
| `product_list` | `page: u64, supplier?: String, product?: String, month?: String` | `Result<PageResponse<ProductList>>` | Paginated product listing with optional filters. 50 items per page. |
| `save_orders` | `orders: Vec<OrderInput>, deletedOrders: Vec<String>` | `Result<()>` | Saves all orders (delete + re-insert) in a single transaction. |
| `expenses_for_month` | `month: String` | `Result<Vec<Expense>>` | Fetches all expenses for a given month (YYYY-MM format). |
| `save_expenses` | `expenses: Vec<ExpenseInput>, month: &str` | `Result<()>` | Deletes existing expenses for the month and inserts new ones in a transaction. |

**Command Registration (main.rs):**
```rust
tauri::generate_handler![
    orders_for_month,
    product_list,
    save_orders,
    expenses_for_month,
    save_expenses,
]
```

### 6.3 API Layer Architecture

**Pattern:** Each Tauri command is a standalone async function in its own module.

**Common Pattern:**
```rust
#[tauri::command]
pub async fn command_name(
    data: State<'_, AppData>,  // Shared AppData with database connection
    param1: Type1,
    param2: Option<Type2>,
) -> Result<ResponseType> {
    // Parse month if needed (via super::util::parse_month)
    // Call repository function
    let result = repository_function(&data.database, ...).await?;
    Ok(result)
}
```

**Utility Module (`api/util.rs`):**
```rust
pub fn parse_month(value: &str) -> Result<Option<(i32, i32)>> {
    // Parses "MM/yyyy" → Some((month, year))
    // Returns None for empty string
    // Returns error for invalid format
}
```

### 6.4 Database Repository Layer

**Pattern:** Repository functions take a generic `&C: ConnectionTrait` (allows both `DatabaseConnection` and `DatabaseTransaction`).

**Order Repository (`order_repository.rs`):**
| Function | Description |
|----------|-------------|
| `list_products(pool, page, filter)` | Paginated product search with supplier/product/month filters. Uses `unidecode` + `like_transform` for fuzzy matching. |
| `select_orders_for_month(pool, month, year)` | Fetches orders with their products for a month range. |
| `delete_orders(transaction, ids)` | Deletes orders by ID list. |
| `insert_order(db, order)` | Inserts a single order. Auto-generates `created_at`/`updated_at`. |

**Product Repository (`product_repository.rs`):**
| Function | Description |
|----------|-------------|
| `delete_order_products(db, order_ids)` | Deletes all products belonging to given order IDs. |
| `insert_product(db, product)` | Inserts a single product. Auto-generates timestamps. |

**Expense Repository (`expense_repository.rs`):**
| Function | Description |
|----------|-------------|
| `find_expenses_for_month(db, month)` | Finds all expenses for a given `YYYY-MM` month string. |
| `save_expenses_month(db, month, expenses)` | Bulk inserts expenses for a month. |
| `delete_expenses_month(db, month)` | Deletes all expenses for a month. |

**Pagination:** Uses SeaORM's `PaginatorTrait`:
```rust
const PAGE_SIZE: u64 = 50;
let paginate = query.paginate(pool, PAGE_SIZE);
let page_count = paginate.num_pages().await?;
let rows = paginate.fetch_page(page - 1).await?;
```

### 6.5 Error Handling Strategy

**File:** `src/error/mod.rs`

**Custom Error Type:**
```rust
pub struct ApiError {
    response: String,   // User-facing error message
    message: String,    // Detailed error message
    trace: Backtrace,   // Captured backtrace (not serialized)
    trace_string: String, // Stringified backtrace
}
```

**Two Error Creation Methods:**
| Method | Use Case | `response` | `message` |
|--------|----------|------------|-----------|
| `ApiError::user_error(str)` | User input errors | The provided string | The provided string |
| `From<T>` impl | Internal/database errors | `"Erro interno"` | The underlying error's `to_string()` |

**Display Behavior:**
- Debug mode: Includes full backtrace in output
- Release mode: No backtrace in output
- All errors are logged via `tracing::error!` before being returned

**Type Alias:**
```rust
pub type Result<T> = std::result::Result<T, ApiError>;
```

Every API function returns `Result<T>` (which is `Result<T, ApiError>`).

### 6.6 Logging Configuration

**Development (debug builds):**
```rust
tracing_subscriber::fmt()
    .with_max_level(tracing::Level::DEBUG)
    .with_test_writer()  // Outputs to console
    .init();
```

**Production (release builds):**
```rust
// Log file: %LOCALAPPDATA%\gessofer-tauri\log.txt
tracing_subscriber::fmt()
    .with_ansi(false)
    .compact()
    .with_max_level(tracing::Level::INFO)
    .with_writer(Arc::new(file))  // File writer
    .init();
```

**Log Levels:**
- Debug: `DEBUG` (development) — all traces
- Release: `INFO` (production) — errors and above

### 6.7 AppData Shared State Pattern

**Definition (`lib.rs`):**
```rust
pub struct AppData {
    pub database: DatabaseConnection,
}
```

**Registration (`main.rs`):**
```rust
let database = tokio::runtime::Runtime::new()
    .unwrap()
    .block_on(async { open_database().await? });

tauri::Builder::default()
    .manage(AppData { database })  // Registered as Tauri state
    .invoke_handler(tauri::generate_handler![...])
    .run(tauri::generate_context!())
```

**Usage in Commands:**
```rust
#[tauri::command]
pub async fn some_command(data: State<'_, AppData>, ...) -> Result<...> {
    let db = &data.database;
    // Use db for queries
}
```

The database connection is created once at app startup using a Tokio runtime, then shared across all Tauri command invocations via Tauri's state management.

---

## 7. Styling & UI Framework

### 7.1 Foundation Sites Integration

**Library:** Foundation Sites v6.9.0

**Initialization:**
```scss
@import "foundation-sites/scss/foundation.scss";
@include foundation-everything($prototype: true);
```

This includes ALL Foundation components (grid, forms, buttons, tables, pagination, callouts, tooltips, dropdowns, top-bar, etc.).

**Foundation Settings Overridden:**
| Variable | Value | Purpose |
|----------|-------|---------|
| `$grid-margin-gutters` | `10px` | Custom gutter size for grid |
| `$button-border` | `0` | Remove button borders |
| `$has-tip-border-bottom` | `0` | Remove tooltip indicator underline |

**Components Used:**
- **Grid System:** `grid-x`, `grid-margin-x`, `cell`, `auto`, `shrink`, `medium-3`, `medium-6`, `medium-9`, `medium-1`, `medium-2`, `small-3`
- **Top Bar:** `top-bar`, `top-bar-left`, `dropdown menu`, `menu vertical`, `menu-text`
- **Forms:** `control`, `input-group`, `input-group-label`, `input-group-field`, `input-group-button`, `form-error`
- **Buttons:** `button`, `button-group`, `is-primary`, `is-secondary`, `clear`, `alert`, `disabled`, `no-gaps`
- **Tables:** `<table>`, `<thead>`, `<tbody>`, `<th>`, `<td>`
- **Pagination:** `pagination`, `pagination-previous`, `pagination-next`
- **Callouts:** `callout`, `callout secondary`
- **Cards:** `card`, `card-section`, `card-order`
- **Tooltips:** `FoundationTooltip` (custom component wrapping `new Tooltip()`)
- **Labels:** `label`, `success label`, `alert label`

### 7.2 CSS Architecture

**File:** `src/style/main.scss`

**Structure:**
1. Foundation settings overrides
2. Foundation import and initialization
3. Custom mixin hooks
4. Font-face declarations
5. Body and element styles
6. Icon helper class

**Custom CSS (in OrderEdit.vue):**
```css
.order-bottom-buttons {
  margin-bottom: 0;
}

.header-sticky {
  position: sticky;
  top: 0;
  z-index: 99999;
  padding-top: 1rem;
  padding-bottom: 0;
  margin-bottom: 0;
  background-color: white;
}

.header-normal {
  margin-bottom: 1rem;
}
```

**AlertContainer scoped CSS:**
```css
.v-enter-active { transition: all 0.5s ease-out; }
.v-leave-active { transition: all 0.8s cubic-bezier(1, 0.5, 0.8, 1); }
.v-enter-from, .v-leave-to { transform: translateX(80px); opacity: 0; }

.alert-absolute {
  position: absolute;
  text-overflow: clip;
  top: 80px;
  right: 20px;
  min-width: 300px;
}
```

### 7.3 Font Usage

| Font | Family Name | Usage | Source |
|------|------------|-------|--------|
| **Roboto** | `"Roboto"` | Body text | `public/fonts/Roboto/Roboto-Regular.woff2` (plus all weights: Light, Medium, Bold, Black, Thin, and their Italic variants) |
| **Raleway** (mapped as "Oswald") | `"Oswald"` | Headings (h1-h5) | `public/fonts/Raleway/Raleway.ttf` |

**Font Declaration:**
```scss
@font-face {
  font-family: "Oswald";
  font-style: normal;
  src: url(./fonts/Raleway/Raleway.ttf) format("truetype");
}

@font-face {
  font-family: "Roboto";
  font-style: normal;
  src: url(./fonts/Roboto/Roboto-Regular.woff2) format("truetype");
}
```

### 7.4 Icon System

**Library:** FontAwesome 6 (via `@fortawesome/vue-fontawesome`)

**Icon Sets Included:**
- `@fortawesome/free-solid-svg-icons` — Primary icons
- `@fortawesome/free-regular-svg-icons` — Secondary icons

**Icons Used in Application:**
| Icon | Usage |
|------|-------|
| `faBuilding` | Supplier field icon |
| `faHammer` | Product filter icon |
| `faCalendar` | Date/month field icon |
| `faBrazilianRealSign` | Currency field icon |
| `faFloppyDisk` | Save button icon |
| `faTrashCan` | Delete/remove icon |
| `faInfo` | Warning/info tooltip icon |
| `faCheck` | Success message icon |
| `faClose` | Error message icon |
| `faAngleLeft`, `faAngleRight` | Pagination arrows |
| `faAnglesLeft`, `faAnglesRight` | First/last page arrows |

### 7.5 Input Masking System

**Library:** Inputmask v5.0.9 (with jQuery)

**Mask Patterns Used:**
| Mask | Format | Example |
|------|--------|---------|
| `99/9999` | Month (MM/yyyy) | `07/2024` |
| `99/99/9999` | Date (dd/MM/yyyy) | `24/07/2024` |

**Initialization:**
```typescript
onMounted(() => {
  if (props.mask) {
    const inputmask = new Inputmask(props.mask);
    inputmask.mask(element.value ?? "");
  }
});
```

### 7.6 Responsive Layout Patterns

**Grid System:** Foundation's responsive grid with breakpoint-based classes:
- `cell shrink` — Content-sized cells
- `cell auto` — Fluid-width cells
- `cell small-3` — 3 columns on small screens and up
- `cell medium-1`, `medium-2`, `medium-3`, `medium-6`, `medium-9` — Responsive column widths
- `grid-x grid-margin-x` — Grid with margins between cells
- `align-justify`, `align-right`, `align-middle` — Alignment utilities

---

## 8. Build & Deployment

### 8.1 Tauri Build Configuration

**File:** `src-tauri/tauri.conf.json`

```json
{
  "productName": "compras-tauri",
  "version": "0.0.0",
  "identifier": "com.gessofer",
  "build": {
    "beforeDevCommand": "pnpm dev",
    "devUrl": "http://localhost:1420",
    "beforeBuildCommand": "pnpm build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [{
      "title": "compras-tauri",
      "width": 1200,
      "height": 720
    }],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  }
}
```

**Key Settings:**
- **Window:** 1200×720 pixels, titled "compras-tauri"
- **CSP:** Disabled (`null`) — no Content Security Policy
- **Bundle targets:** All platforms (Windows, macOS, Linux)
- **Windows Subsystem:** `windows_subsystem = "windows"` (no console window in release)

### 8.2 Vite Configuration

**File:** `vite.config.ts`

```typescript
export default defineConfig(async () => ({
  plugins: [vue()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: { ignored: ["**/src-tauri/**"] },
  },
  resolve: {
    alias: { "@": path.join(__dirname, "src") },
  },
}));
```

**Key Settings:**
- **Port:** 1420 (fixed, strict)
- **Path alias:** `@/` → `./src/`
- **Ignored watch:** `src-tauri/**` (don't restart Vite on Rust changes)
- **Clear screen:** false (prevents obscuring Rust errors)

### 8.3 Cargo.toml Dependencies

**Production Dependencies:**
| Crate | Version | Purpose |
|-------|---------|---------|
| `tauri` | 2.0.0-beta | Tauri framework |
| `tauri-plugin-shell` | 2.0.0-beta.9 | Shell plugin |
| `sea-orm` | 0.11.0 | ORM (SQLite via sqlx) |
| `serde` | 1.0 | Serialization/deserialization |
| `serde_json` | 1.0 | JSON handling |
| `chrono` | 0.4.23 | Date/time handling |
| `tokio` | 1.25.0 | Async runtime |
| `tracing` | 0.1.37 | Structured logging |
| `tracing-subscriber` | 0.3.16 | Logging subscriber |
| `tracing-appender` | 0.2.3 | File logging |
| `tracing-log` | 0.2.0 | Log compatibility |
| `anyhow` | 1.0.69 | Error handling |
| `unidecode` | 0.3.0 | ASCII normalization |
| `dotenv` | 0.15.0 | Environment variables |
| `hyper-tls` | 0.6 | HTTP client (unused?) |

**Build Dependencies:**
| Crate | Version | Purpose |
|-------|---------|---------|
| `tauri-build` | 2.0.0-beta | Build script helper |
| `dotenv` | 0.15.0 | Environment variables in build |

**Features:**
- `custom-protocol` (default): Enables custom protocol for local file loading
- `e2e`: Enables E2E test mode (different database path)

### 8.4 Frontend Build Pipeline

```
Source (.vue, .ts, .scss)
  ↓
Vite (ESM bundler)
  ↓ (Vue plugin transforms .vue SFCs)
  ↓ (Sass compiler processes .scss)
  ↓ (TypeScript type-checking via vue-tsc)
Bundled Output (ESM modules)
  ↓
dist/ directory
  ↓
Tauri bundles into native executable
```

**Scripts:**
| Script | Command | Description |
|--------|---------|-------------|
| `dev` | `vite` | Development server |
| `build` | `vue-tsc --noEmit && vite build` | Type-check + production build |
| `build-only` | `vite build` | Build without type-checking |
| `type-check` | `vue-tsc --noEmit` | TypeScript type checking |
| `lint` | `eslint . --fix` | ESLint with auto-fix |
| `tauri` | `tauri` | Tauri CLI commands |

**TypeScript Configuration:**
- Target: ES2020
- Module: ESNext (bundler mode)
- Strict mode enabled
- JSX: preserve (for .vue files)
- Path aliases: `@/*` → `./src/*`

### 8.5 E2E Test Configuration

**File:** `wdio.conf.ts`

**Framework:** WebdriverIO v8 with Mocha

**Test Specs:** `./test/specs/**/*.ts`

**Preparation (`onPrepare`):**
1. Clean up any existing temp database files
2. Copy `./src-tauri/main.db` to `%TEMP%\tmp-gessofer-tauri.db`
3. If `SKIP_COMPILE` env var is not set:
   - Run `pnpm build` (frontend build)
   - Run `cargo build --release --features e2e` (Rust build with E2E feature)

**Session Management:**
- Spawns `tauri-driver` process before tests
- Kills `tauri-driver` after tests

**Application Binary:** `./src-tauri/target/release/gessofer-tauri.exe`

**Connection:** Local WebDriver on `127.0.0.1:4444`

---

## 9. Testing

### 9.1 E2E Test Suite Structure

```
test/
├── specs/
│   └── orderEdit.e2e.ts      # OrderEdit view tests
└── pageobjects/
    └── page.ts                # Base page object (unused placeholder)
```

### 9.2 Test Scenarios

**File:** `test/specs/orderEdit.e2e.ts`

**Test Suite:** "Order Edit view test"

| # | Test Name | Description |
|---|-----------|-------------|
| 1 | "should create simple order" | Creates an order with 1 product, verifies all fields display correctly including auto-calculated total |
| 2 | "should create order and distribute freight with one item" | Creates order with freight, clicks "Distribuir frete", verifies price recalculation |
| 3 | "should create order and distribute freight and unloading with multiple items" | Creates order with 3 products, freight, and unloading, verifies proportional freight distribution |

**Test Data Example (Test 3):**
```
Supplier: "Fornecedor com frete e descarga"
Date: "24/07/2024"
Freight: 1000 cents
Unloading: 3000 cents
Products:
  Item 1: qty=100, price=150 → expected new price="1,82", total="182,00"
  Item 2: qty=1,   price=1000 → expected new price="12,10", total="12,10"
  Item 3: qty=3,   price=1005 → expected new price="12,16", total="36,48"
Grand total displayed: "R$ 230,57"
```

### 9.3 Test Helpers

**`navigateToPage()`:**
1. Clicks `#nav-menu-orders` dropdown
2. Clicks `#nav-link-orders-create` link
3. Waits for `#btn-add-order` to be clickable

**`createOrder()`:**
1. Clicks `#btn-add-order`
2. Scrolls the last `.card-order` into view
3. Verifies it's displayed in viewport
4. Returns the order card element

**`fillOrder(card, data)`:**
1. Sets supplier, freight, unloading, date fields
2. For each product: fills name, quantity, price in the last product row
3. Clicks the last product input to trigger auto-add of empty row

**`currencyToString(value)`:**
```typescript
function currencyToString(value: number) {
  return value / 100;  // Converts cents to display value for test input
}
```

---

## 10. Migration Mapping (for Python Port)

### 10.1 Vue → PySide6 Component Mapping

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

### 10.2 Pinia Store → PyQt Signal/Slot Mapping

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

### 10.3 Tauri Commands → Python Backend Mapping

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

### 10.4 SeaORM SQLite → Python SQLite Mapping

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

### 10.5 Yup/vee-validate → Python Validation Mapping

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

### 10.6 Foundation Sites → Qt Stylesheet Mapping

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

### 10.7 Luxon Date Library → Python datetime Mapping

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

### 10.8 Inputmask → Qt QLineEdit Mapping

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

---

## Appendix A: Complete File Index

### Frontend Files
| File | Purpose |
|------|---------|
| `src/App.vue` | Root component (layout) |
| `src/main.ts` | Application entry point |
| `src/router/index.ts` | Vue Router configuration |
| `src/style/main.scss` | Global styles + Foundation setup |
| `src/views/ProductList.vue` | Product list view |
| `src/views/OrderEdit.vue` | Order editor view |
| `src/views/ExpensesView.vue` | Expenses list view |
| `src/views/ExpensesEdit.vue` | Expenses editor view |
| `src/views/AboutView.vue` | About page |
| `src/components/AppNavbar.vue` | Navigation bar |
| `src/components/DataTable.vue` | Generic data table |
| `src/components/FormInput.vue` | Reusable form input |
| `src/components/MonthQueryForm.vue` | Month selector |
| `src/components/AlertContainer.vue` | Global alert display |
| `src/components/MessageContainer.vue` | Success/error messages |
| `src/components/FoundationTooltip.vue` | Tooltip wrapper |
| `src/components/ExpensesTable.vue` | Expenses table |
| `src/util/date.ts` | Date utilities |
| `src/util/currency.ts` | Currency utilities |
| `src/util/validation.ts` | Yup validation extensions |
| `src/util/parseNfe.ts` | NFe XML parser |
| `src/util/ids.ts` | ID generator |
| `src/stores/alert.ts` | Pinia alert store |
| `src/model/OrderForm.ts` | Order form type |
| `src/model/OrderResponse.ts` | Order DTO type |
| `src/model/Order.ts` | Order/Product types |
| `src/model/Expense.ts` | Expense type |
| `src/model/ExpenseForm.ts` | Expense form type |
| `src/model/ProductList.ts` | Product list type |
| `src/model/TableResponse.ts` | Paginated response type |
| `src/globals.d.ts` | Yup type extensions |
| `src/vite-env.d.ts` | Vite type declarations |

### Backend Files
| File | Purpose |
|------|---------|
| `src-tauri/src/main.rs` | Entry point, app setup |
| `src-tauri/src/lib.rs` | Library root, AppData struct |
| `src-tauri/src/migrate.rs` | Database migration binary |
| `src-tauri/src/api/mod.rs` | API module exports |
| `src-tauri/src/api/orders_for_month.rs` | Orders for month command |
| `src-tauri/src/api/product_list.rs` | Product list command |
| `src-tauri/src/api/save_orders.rs` | Save orders command |
| `src-tauri/src/api/save_expenses.rs` | Save expenses command |
| `src-tauri/src/api/util.rs` | Month parsing utility |
| `src-tauri/src/database/mod.rs` | Database module exports |
| `src-tauri/src/database/connect.rs` | Database connection logic |
| `src-tauri/src/database/order_repository.rs` | Order queries |
| `src-tauri/src/database/product_repository.rs` | Product queries |
| `src-tauri/src/database/expense_repository.rs` | Expense queries |
| `src-tauri/src/database/entity/order.rs` | Order entity |
| `src-tauri/src/database/entity/product.rs` | Product entity |
| `src-tauri/src/database/entity/expense.rs` | Expense entity |
| `src-tauri/src/database/entity/prelude.rs` | Entity prelude |
| `src-tauri/src/database/entity_old/` | Legacy entities |
| `src-tauri/src/error/mod.rs` | Error handling |
| `src-tauri/src/model/order.rs` | API Order/Product models |
| `src-tauri/src/model/expense.rs` | API Expense model |
| `src-tauri/src/model/page_response.rs` | Paginated response model |
| `src-tauri/src/model/product_list.rs` | Product list model |

### Configuration Files
| File | Purpose |
|------|---------|
| `package.json` | Node.js dependencies and scripts |
| `tsconfig.json` | TypeScript configuration |
| `vite.config.ts` | Vite bundler configuration |
| `tauri.conf.json` | Tauri app configuration |
| `Cargo.toml` | Rust dependencies |
| `wdio.conf.ts` | WebdriverIO E2E test configuration |
| `.eslintrc.cjs` | ESLint configuration |
| `.prettierrc.json` | Prettier configuration |
| `src-tauri/capabilities/migrated.json` | Tauri permissions |

---

## Appendix B: Business Rules Summary

1. **Currency is always stored as integer cents** — never use floating-point for money.
2. **Freight distribution** reallocates freight + unloading costs proportionally across all products based on their total values.
3. **Auto-save** runs every 30 seconds but only when the form has been modified AND passes validation.
4. **XML import** adds IPI and ICMS-ST tax values to product prices before calculating unit prices.
5. **Product rows** auto-add when the last row is filled, auto-remove when empty rows are edited.
6. **Search normalization** uses `unidecode` to convert accented characters to ASCII for fuzzy matching.
7. **Save strategy** is "delete all, insert all" — entire order/product sets are replaced in a transaction.
8. **Expense saving** deletes all expenses for the month and re-inserts, ensuring no duplicates.
9. **No authentication** — the app assumes a single trusted local user.
10. **Database is local** — stored in `%LOCALAPPDATA%\gessofer-tauri\main.db` on Windows.

---

*End of Documentation.*
