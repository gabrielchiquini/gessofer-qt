> **Part of:** [Gessofer-Tauri Documentation](./README.md)

# Database Schema & Data Model

## 2.1 Complete Current SQLite Schema (New Schema)

The application uses **three tables** in the current database (`main.db`).

### Table: `ORDER`

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

### Table: `PRODUCT`

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

### Table: `EXPENSE`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `ID` | INTEGER | PRIMARY KEY, auto_increment | Auto-incrementing integer ID |
| `MONTH` | TEXT | NOT NULL | Month in `YYYY-MM` format |
| `DESCRIPTION` | TEXT | NOT NULL | Expense description |
| `VALUE` | INTEGER | NOT NULL | Expense amount in cents |
| `CREATED_AT` | DATETIME | NOT NULL | Row creation timestamp |
| `UPDATED_AT` | DATETIME | NOT NULL | Last update timestamp |

## 2.2 Legacy Database Schema (Old Tables)

The migration tool (`migrate.rs`) reads from a legacy database file (`main-2025-12.db`) with these tables:

### Table: `NOTA` (Invoice)

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

### Table: `PRODUTOS` (Products)

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

### Table: `EXPENSES` (Expenses)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NOT NULL | Auto-increment primary key |
| `name` | TEXT | YES | Expense name/description |
| `value` | DOUBLE | YES | Expense value (float) |
| `month` | DOUBLE | YES | Month number (1-12) |
| `year` | DOUBLE | YES | Year |
| `createdAt` | DATETIME | NOT NULL | Creation timestamp |
| `updatedAt` | DATETIME | NOT NULL | Update timestamp |

## 2.3 Entity Relationships

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

## 2.4 Data Migration Strategy

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

## 2.5 Database File Locations and Discovery Logic

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

## 2.6 Field Naming Conventions

| Context | Convention | Examples |
|---------|-----------|----------|
| **Database columns** | UPPERCASE_SNAKE_CASE | `SUPPLIER`, `NFE_KEY`, `TOTAL_PRICE` |
| **Rust struct fields** | snake_case | `supplier`, `nfe_key`, `total_price` |
| **JSON API fields** | camelCase | `supplier`, `nfeKey`, `totalPrice` |
| **Vue/TypeScript model fields** | camelCase | `supplier`, `nfeKey`, `totalPrice` |
| **Normalized fields** | `*_normalized` suffix | `supplier_normalized`, `name_normalized` |
