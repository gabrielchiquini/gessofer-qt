> **Part of:** [Gessofer-Tauri Documentation](./README.md)

# Testing

## 9.1 E2E Test Suite Structure

```
test/
├── specs/
│   └── orderEdit.e2e.ts      # OrderEdit view tests
└── pageobjects/
    └── page.ts                # Base page object (unused placeholder)
```

## 9.2 Test Scenarios

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

## 9.3 Test Helpers

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
