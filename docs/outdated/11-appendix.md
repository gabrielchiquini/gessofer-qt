> **Part of:** [Gessofer-Tauri Documentation](README.md)

# Appendix A: Complete File Index

## Frontend Files

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

## Backend Files

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

## Configuration Files

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

# Appendix B: Business Rules Summary

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
