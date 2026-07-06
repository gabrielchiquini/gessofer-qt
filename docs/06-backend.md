> **Part of:** [Gessofer-Tauri Documentation](./README.md)

# Backend — Rust/Tauri Architecture

## 6.1 Tauri 2 App Structure

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

## 6.2 Tauri Commands API Surface

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

## 6.3 API Layer Architecture

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

## 6.4 Database Repository Layer

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

## 6.5 Error Handling Strategy

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

## 6.6 Logging Configuration

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

## 6.7 AppData Shared State Pattern

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
