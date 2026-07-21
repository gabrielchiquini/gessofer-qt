# Implementation Plan: Split OrderCardWidget into Header and Items Cards

## Summary

This plan extracts the monolithic `OrderCardWidget` into two focused widgets — `OrderHeaderCard` (supplier, date, freight, unloading) and `OrderItemsCard` (product rows + footer with total + distribute button). The `OrderEditDialog` is updated to host both widgets in a vertical layout. All existing behavior, signals, and data flow is preserved.

## Critical Observation: `nfe_key_input` Bug

The current `OrderCardWidget` references `self.nfe_key_input` in three places (`get_order_data`, `_set_from_order_data`, `clear`) but **this widget is never created** in `__init__`. This is a latent bug — `AttributeError` would be raised at runtime if `get_order_data()` is called on a new order (before any save), or when `clear()` is called. The plan below does **not** fix this bug as part of the refactor (to keep scope tight), but it **notes** it and the implementer should be aware. The `nfe_key_input` field should either be added to the header card or the references should be removed. For this plan, we **remove the references** to avoid introducing a new field during the split, and file a separate TODO.

---

## Files to Create

### 1. `src/frontend/order_header_card.py`

**Purpose:** Encapsulates the four order header fields (supplier, date, freight, unloading) in its own styled card frame.

**Key contents:**
- **Class:** `OrderHeaderCard(QWidget)`
- **Imports:**
  ```python
  from __future__ import annotations

  from PySide6.QtCore import Signal
  from PySide6.QtGui import QRegularExpressionValidator
  from PySide6.QtWidgets import (
      QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget,
  )

  from frontend.components.card import Card
  from backend.utils.currency import cents_to_display, parse_currency_to_cents
  from backend.utils.date import iso_to_br_date
  ```
  (No bridge model imports needed — this widget only reads/writes its own fields.)

- **Private attribute:**
  - `_card: Card` — the `Card` component that wraps all content.

- **Public attributes (QLineEdit instances, same names as before):**
  - `supplier_input: QLineEdit`
  - `date_input: QLineEdit`
  - `freight_input: QLineEdit`
  - `unloading_input: QLineEdit`

- **Signal:**
  - `order_changed: Signal = Signal()` — emitted whenever any header field changes, or when data is loaded via `_set_from_order_data`.

- **`__init__(self, parent: QWidget | None = None)`** — no `order_data` parameter. Creates the four inputs, sets up the horizontal layout of vertical label+input pairs, creates a `Card` instance, calls `card.set_title("Dados do pedido")`, passes the header layout to `card.set_content()`, and connects all four inputs to `_on_header_changed`.

- **`_on_header_changed(self) -> None`** — emits `order_changed`.

- **`get_supplier(self) -> str`** — returns `self.supplier_input.text().strip()`.

- **`get_date(self) -> str`** — returns `self.date_input.text().strip()`.

- **`get_freight_cents(self) -> int`** — returns `parse_currency_to_cents(self.freight_input.text())`.

- **`get_unloading_cents(self) -> int`** — returns `parse_currency_to_cents(self.unloading_input.text())`.

- **`set_supplier(self, text: str) -> None`** — sets `self.supplier_input.setText()`.

- **`set_date_br(self, text: str) -> None`** — sets `self.date_input.setText()`.

- **`set_freight_cents(self, cents: int) -> None`** — sets `self.freight_input.setText(cents_to_display(cents))`.

- **`set_unloading_cents(self, cents: int) -> None`** — sets `self.unloading_input.setText(cents_to_display(cents))`.

- **`set_order_data(self, order_data: OrderDict) -> None`** — loads all four fields from an `OrderDict`. Emits `order_changed`.

- **`clear(self) -> None`** — clears all four fields.

- **`validate(self) -> tuple[bool, list[str]]`** — validates date format and supplier required. Returns `(True, [])` if valid, `(False, [errors])` if not.

- **Card styling:** Use the `Card` component from `src/frontend/components/card.py`. The card provides three sections: header, content, and footer.

**Header:** Call `card.set_title("Dados do pedido")` to render the title in the card's built-in header section (bold text with separator line). **Do not** add a separate `QLabel` at the top of the content area — the `Card` component already handles header display via `set_title()`.

**Content:** Pass the header fields layout to `card.set_content()`.

**Footer:** Not used for the header card.

---

### 2. `src/frontend/order_items_card.py`

**Purpose:** Encapsulates the product rows container, the total label, and the "Distribuir frete" button in its own styled card frame.

**Key contents:**
- **Class:** `OrderItemsCard(QWidget)`
- **Imports:**
  ```python
  from __future__ import annotations

  import uuid
  from typing import Any

  from PySide6.QtCore import Qt, Signal
  from PySide6.QtGui import QRegularExpressionValidator
  from PySide6.QtWidgets import (
      QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
  )

  from frontend.components.card import Card
  from bridge.models.order import OrderDict, OrderInputDict
  from bridge.models.product import ProductDict
  from frontend.business import distribute_freight
  from frontend.product_row_widget import ProductRowWidget
  from backend.utils.currency import cents_to_display, parse_currency_to_cents
  ```

- **Private attribute:**
  - `_card: Card` — the `Card` component that wraps all content.

- **Public attributes:**
  - `products_layout: QVBoxLayout` — the layout that holds `ProductRowWidget` instances
  - `products_total_label: QLabel` — displays "Total dos produtos: R$ X,XX"
  - `distribute_button: QPushButton` — "Distribuir frete" button
  - `_product_rows: list[ProductRowWidget]` — internal list of row widgets

- **Signals:**
  - `order_changed: Signal = Signal()` — emitted whenever product rows change (add, remove, content change, freight distribution).

- **`__init__(self, parent: QWidget | None = None)`** — creates the products layout, total label, distribute button. Creates a `Card` instance, calls `card.set_title("Itens")`, passes the products layout to `card.set_content()`, builds the footer via `card.build_footer()`, sets the total label + distribute button as the footer via `card.set_footer()`, and connects `distribute_button.clicked` to `_on_distribute_freight`. If `order_data` is passed (for backward compatibility during migration), pre-fills rows. Otherwise, adds one empty row.

- **`_add_empty_row(self) -> ProductRowWidget`** — same as current: creates `ProductRowWidget`, appends to `_product_rows`, adds to `products_layout`, connects `row_changed`, calls `_update_delete_buttons`.

- **`_on_row_changed(self) -> None`** — same auto-add/auto-remove logic as current. Emits `order_changed`.

- **`_update_delete_buttons(self) -> None`** — same logic.

- **`_on_distribute_freight(self) -> None`** — same as current: calls `distribute_freight`, updates price fields in existing rows. Emits `order_changed`.

- **`get_products_total(self) -> int`** — same as current: sums `parse_currency_to_cents(row.total_input.text())` for all rows.

- **`validate(self) -> tuple[bool, list[str]]`** — validates each product row. Returns combined results.

- **`get_order_data(self) -> OrderInputDict`** — collects supplier/date/etc. from the **header card** (which must be passed or referenced). **This is the key API change:** `OrderItemsCard` no longer has access to header fields. It needs the header data from `OrderHeaderCard`.

  **Option A (preferred):** `OrderItemsCard.get_order_data()` returns only the products list as `list[ProductDict]`. The dialog assembles the full `OrderInputDict` by combining header card data + items card data.

  **Option B:** `OrderItemsCard` stores a reference to the `OrderHeaderCard` and reads header fields internally.

  **This plan recommends Option A** — it keeps widgets loosely coupled. The `OrderEditDialog` becomes the coordinator that reads from both cards and assembles the final dict.

- **`set_order_data(self, order_data: OrderDict) -> None`** — replaces product rows with those from `order_data["products"]`.

- **`clear(self) -> None`** — removes all rows, adds one empty row.

- **`add_row(self) -> ProductRowWidget`** — public method to add a row (for XML import or other callers).

- **`remove_row_at(self, index: int) -> None`** — public method to remove a row at a given index.

- **`get_product_rows(self) -> list[ProductRowWidget]`** — returns the `_product_rows` list (for external access if needed).

- **Card styling:** Use the `Card` component from `src/frontend/components/card.py`. The card provides three sections: header, content, and footer.

**Header:** Call `card.set_title("Itens")` to render the title in the card's built-in header section (bold text with separator line). **Do not** add a separate `QLabel` at the top of the content area — the `Card` component already handles header display via `set_title()`.

**Content:** Pass the product rows layout to `card.set_content()`.

**Footer:** Use `card.build_footer()` then `card.set_footer()` to place the total label and "Distribuir frete" button in the card's footer section (after the separator line).

---

## Files to Modify

### 3. `src/frontend/order_edit_dialog.py`

**Current state:** Creates a single `OrderCardWidget` (`self.order_card`), accesses its attributes directly (`self.order_card.validate()`, `self.order_card.get_order_data()`, `self.order_card.get_products_total()`, `self.order_card.products_total_label`, `self.order_card.distribute_button`, `self.order_card._is_new`, `self.order_card._order_id`).

**Changes needed:**

1. **Replace import:**
   ```python
   # Before:
   from frontend.order_card_widget import OrderCardWidget

   # After:
   from frontend.order_header_card import OrderHeaderCard
   from frontend.order_items_card import OrderItemsCard
   ```

2. **Replace `self.order_card` with two attributes:**
   ```python
   self.header_card: OrderHeaderCard
   self.items_card: OrderItemsCard
   ```

3. **Update `__init__` layout:**
   - Create `self.header_card = OrderHeaderCard(self)`
   - Create `self.items_card = OrderItemsCard(self)`
   - If `order_id` exists and data is fetched, call:
     ```python
     self.header_card.set_order_data(order_data)
     self.items_card.set_order_data(order_data)
     ```
   - Layout: vertical layout adds `header_card` first, then `items_card`, then message label, then footer buttons.

4. **Update `_on_save`:**
   ```python
   # Before:
   valid, errors = self.order_card.validate()
   order_data = self.order_card.get_order_data()
   if not self.order_card._is_new:
       deleted_ids = [self.order_card._order_id]

   # After:
   # Validate header
   header_valid, header_errors = self.header_card.validate()
   # Validate items
   items_valid, items_errors = self.items_card.validate()

   all_errors = header_errors + items_errors
   if not (header_valid and items_valid):
       self._show_message("Há campos inválidos: " + "; ".join(all_errors), "error")
       return

   # Assemble full order data from both cards
   order_data = {
       "id": self._order_id,  # stored in dialog
       "date": self.header_card.get_date(),
       "supplier": self.header_card.get_supplier(),
       "nfeKey": "",  # BUG: nfe_key_input doesn't exist; see note above
       "freight": self.header_card.get_freight_cents(),
       "unloading": self.header_card.get_unloading_cents(),
       "products": self.items_card.get_products_list(),  # new method
   }

   if not self._is_new:
       deleted_ids = [self._order_id]
   ```

5. **Store `_order_id` and `_is_new` in the dialog** (moved from `OrderCardWidget`):
   ```python
   self._order_id: str = order_data["id"] if order_data else str(uuid.uuid4())
   self._is_new: bool = order_data is None
   ```

6. **Update `_on_card_changed`:**
   ```python
   # Before:
   total_cents = self.order_card.get_products_total()
   self.order_card.products_total_label.setText(
       f"Total dos produtos: {cents_to_display(total_cents)}"
   )
   valid, _ = self.order_card.validate()
   can_distribute = valid and total_cents > 0
   self.order_card.distribute_button.setEnabled(can_distribute)

   # After:
   total_cents = self.items_card.get_products_total()
   self.items_card.products_total_label.setText(
       f"Total dos produtos: {cents_to_display(total_cents)}"
   )
   header_valid, _ = self.header_card.validate()
   items_valid, _ = self.items_card.validate()
   can_distribute = header_valid and items_valid and total_cents > 0
   self.items_card.distribute_button.setEnabled(can_distribute)
   ```

7. **Signal connections:**
   ```python
   self.header_card.order_changed.connect(self._on_card_changed)
   self.items_card.order_changed.connect(self._on_card_changed)
   ```

8. **Remove `self.order_card` references entirely.**

---

### 4. `src/frontend/order_card_widget.py`

**Decision: Delete this file.**

**Reason:** After splitting, all of `OrderCardWidget`'s functionality is distributed between `OrderHeaderCard` and `OrderItemsCard`. There is no remaining content to keep. The `OrderEditDialog` no longer imports from this file. No other file in the project imports from this file (confirmed by grep).

**Steps:**
1. Verify no other imports (already confirmed — only `order_edit_dialog.py` imported it).
2. Delete the file.
3. If any test files exist that import it, update them (none exist yet).

---

## Files to NOT Modify

- **`src/frontend/product_row_widget.py`** — unchanged. It is used by `OrderItemsCard` exactly as before.
- **`src/frontend/order_edit_list.py`** — unchanged. It only imports `OrderEditDialog` (indirectly via `from frontend.order_edit_dialog import OrderEditDialog`).
- **`src/frontend/business.py`** — unchanged.
- **`src/bridge/models/order.py`** — unchanged.
- **`src/bridge/models/product.py`** — unchanged.
- **`src/frontend/__init__.py`** — unchanged.

---

## Data Model Changes

None. The `OrderDict` and `OrderInputDict` TypedDicts are unchanged. The data flow is the same — just assembled from two widgets instead of one.

## API Changes

**Breaking changes to the public API of the order editing subsystem:**

| Before | After | Notes |
|--------|-------|-------|
| `OrderCardWidget.validate()` | `OrderHeaderCard.validate()` + `OrderItemsCard.validate()` | Dialog must call both and combine errors |
| `OrderCardWidget.get_order_data()` | `OrderHeaderCard.get_supplier()`, `get_date()`, `get_freight_cents()`, `get_unloading_cents()` + `OrderItemsCard.get_products_list()` | Dialog assembles the full dict |
| `OrderCardWidget.get_products_total()` | `OrderItemsCard.get_products_total()` | Moved to items card |
| `OrderCardWidget.products_total_label` | `OrderItemsCard.products_total_label` | Moved to items card |
| `OrderCardWidget.distribute_button` | `OrderItemsCard.distribute_button` | Moved to items card |
| `OrderCardWidget._is_new` | `OrderEditDialog._is_new` | Moved to dialog |
| `OrderCardWidget._order_id` | `OrderEditDialog._order_id` | Moved to dialog |
| `OrderCardWidget.order_changed` | `OrderHeaderCard.order_changed` + `OrderItemsCard.order_changed` | Both emit; dialog connects to both |

**Non-breaking:** `ProductRowWidget` API is unchanged.

---

## State Management Changes

- **`_order_id` and `_is_new`** move from `OrderCardWidget` to `OrderEditDialog`. The dialog is the only place that needs to know whether the order is new (for the delete-then-insert pattern in `save_orders`).
- **`_product_rows`** stays in `OrderItemsCard` (it owns product row management).
- **Signals:** Both header and items cards emit `order_changed`. The dialog connects to both and reacts by updating the total label and distribute button state.

---

## UI/UX Changes

### New Layout in `OrderEditDialog`

```
┌──────────────────────────────────────┐
│  [OrderEditDialog - "Editar Pedido"] │
├──────────────────────────────────────┤
│ ┌──────────────────────────────────┐ │
│ │ Dados do pedido                  │ │  ← Card header (bold title + separator)
│ ├──────────────────────────────────┤ │
│ │ ┌──────────┬───────────┬───────┐ │ │  ← Card content
│ │ │ Fornecedor│   Data   │ Frete │ │ │
│ │ │ [_______]│[99/99/9999]│ [___]│ │ │
│ │ └──────────┴───────────┴───────┘ │ │
│ │ Descarga                         │ │
│ │ [_______]                        │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ Itens                            │ │  ← Card header (bold title + separator)
│ ├──────────────────────────────────┤ │
│ │ ┌──────────────────────────────┐ │ │  ← Card content
│ │ │ [Produto] [Qtde] [R$ 0,00]   │ │ │
│ │ │               [R$ 0,00]  [✕] │ │ │
│ │ └──────────────────────────────┘ │ │
│ │ ┌──────────────────────────────┐ │ │
│ │ │ [Produto] [Qtde] [R$ 0,00]   │ │ │
│ │ │               [R$ 0,00]  [✕] │ │ │
│ │ └──────────────────────────────┘ │ │
│ ├──────────────────────────────────┤ │
│ │ Total dos produtos: R$ 0,00      │ │  ← Card footer (after separator)
│ │               [Distribuir frete] │ │
│ └──────────────────────────────────┘ │
│                                      │
│  [Message label]                     │
│                                      │
│  [Salvar]              [Fechar]      │
└──────────────────────────────────────┘
```

Each card is a `Card` component (a `QFrame` subclass) with white background, rounded corners (`border-radius: 6px`), subtle border (`1px solid #d0d0d0`), and the `Card` component's built-in header section (bold title text + separator line) and optional footer section (separator line + footer area). The dialog's main layout is a `QVBoxLayout` with:
1. `header_card` (no stretch)
2. `items_card` (stretch = 1, so it takes remaining space)
3. `message_label` (no stretch)
4. Footer frame with save/close buttons

---

## Migration Notes

### Attribute Re-routing Table

All direct attribute accesses from `OrderEditDialog` to `OrderCardWidget` must be re-routed:

| Old access | New access |
|------------|-----------|
| `self.order_card.validate()` | `self.header_card.validate()` + `self.items_card.validate()` |
| `self.order_card.get_order_data()` | Assembled from both cards (see `_on_save` above) |
| `self.order_card.get_products_total()` | `self.items_card.get_products_total()` |
| `self.order_card.products_total_label` | `self.items_card.products_total_label` |
| `self.order_card.distribute_button` | `self.items_card.distribute_button` |
| `self.order_card._is_new` | `self._is_new` (on dialog) |
| `self.order_card._order_id` | `self._order_id` (on dialog) |
| `self.order_card.order_changed` | `self.header_card.order_changed` + `self.items_card.order_changed` |

### `nfe_key_input` Bug

The current `OrderCardWidget` references `self.nfe_key_input` in `get_order_data()` (line 239), `_set_from_order_data()` (line 304), and `clear()` (line 331), but this widget is never created in `__init__`. This means:
- `get_order_data()` raises `AttributeError` on a new order
- `_set_from_order_data()` raises `AttributeError` when loading an existing order
- `clear()` raises `AttributeError`

**This plan removes these references** — the `nfeKey` field is set to an empty string `""` in the assembled order data. A separate issue should be filed to either:
- Add an `nfe_key_input` field to the header card (if the feature is needed), or
- Remove all `nfeKey` references if the field is deprecated.

---

## Testing Considerations

No test files currently exist. When tests are written:

1. **`test_order_header_card.py`** — Unit tests for:
   - `validate()` with valid/invalid dates, empty supplier
   - `set_order_data()` populates fields correctly
   - `clear()` resets all fields
   - `get_*` methods return correct values
   - `order_changed` signal emits on field changes

2. **`test_order_items_card.py`** — Unit tests for:
   - `_add_empty_row()` creates row and connects signals
   - `_on_row_changed()` auto-adds when last row filled
   - `_on_row_changed()` auto-removes when non-last row emptied
   - `get_products_total()` sums correctly
   - `validate()` validates each row
   - `clear()` resets to one empty row
   - `get_products_list()` returns correct list

3. **`test_order_edit_dialog.py`** — Integration tests for:
   - Dialog creates both cards
   - `_on_save()` assembles data from both cards
   - `_on_card_changed()` updates total and button state
   - Save emits `order_saved` on success

---

## Risks and Considerations

### 1. `nfe_key_input` AttributeError (Critical)
The current code has a latent `AttributeError` bug. If the current code is running in production and `get_order_data()` is ever called, it crashes. The plan removes these references but a separate fix is needed.

### 2. Breaking Change — `OrderCardWidget` Deleted
If any external code (tests, plugins, other modules) imports `OrderCardWidget`, it will break. **Mitigation:** Verified via grep that only `order_edit_dialog.py` imports it, and that file is updated in the same PR.

### 3. Signal Duplication
Both cards emit `order_changed`. The dialog connects to both. This means `_on_card_changed` may be called twice for a single user action (e.g., changing a product row triggers `items_card.order_changed`, but if the user also changed a header field, both fire). **Mitigation:** This is harmless — `_on_card_changed` is idempotent (it just reads current values and updates the UI).

### 4. Layout Spacing
The two-card layout introduces a gap between cards. The implementer should ensure consistent spacing — use `layout.setSpacing(8)` on the dialog's main layout (same as the current card's internal spacing) to avoid visual inconsistency.

### 5. `Card` Component Header/Footer Behavior
The `Card` component uses lazy header building: `set_title()` only builds the header section when a non-empty string is passed, and `set_footer()` only builds the footer when `build_footer()` is called first. For `OrderHeaderCard`, only the header is used (no footer). For `OrderItemsCard`, both header and footer are used. The implementer must call `card.build_footer()` before `card.set_footer()` for the items card.

**Note:** The `Card._build_header()` method has a misplaced docstring on line 71 of `card.py` (it appears between the separator creation and the `insertWidget` calls). This is cosmetic and doesn't affect behavior, but the implementer may want to fix it as a minor cleanup.

### 6. `OrderItemsCard.get_order_data()` API Change
The plan recommends Option A (dialog assembles the dict) over Option B (items card references header card). This keeps widgets decoupled but requires the dialog to do more assembly work. If the dialog becomes complex, Option B can be revisited.

---

## Implementation Order

1. **Create `src/frontend/order_header_card.py`** — new widget with header fields, validation, data access methods.
2. **Create `src/frontend/order_items_card.py`** — new widget with product rows, footer, freight distribution, data access methods.
3. **Update `src/frontend/order_edit_dialog.py`** — replace `OrderCardWidget` with both new widgets, update layout, re-route attribute accesses, store `_order_id`/`_is_new` on dialog.
4. **Delete `src/frontend/order_card_widget.py`** — no longer needed.
5. **Run tests** — `pytest` to verify nothing is broken.
6. **Run the app** — `python src/main.py` to verify visual appearance and behavior.
7. **File separate TODO** for `nfe_key_input` bug fix.

---

## Summary of All Changes

| Action | File | What |
|--------|------|------|
| **Create** | `src/frontend/order_header_card.py` | `OrderHeaderCard` widget — header fields in a styled card |
| **Create** | `src/frontend/order_items_card.py` | `OrderItemsCard` widget — product rows + footer in a styled card |
| **Modify** | `src/frontend/order_edit_dialog.py` | Replace `OrderCardWidget` with both new widgets; re-route all attribute accesses; move `_order_id`/`_is_new` to dialog; assemble order data from both cards |
| **Delete** | `src/frontend/order_card_widget.py` | Entire file removed — functionality distributed to the two new widgets |
| **No change** | `src/frontend/product_row_widget.py` | Used as-is by `OrderItemsCard` |
| **No change** | `src/frontend/order_edit_list.py` | Only depends on `OrderEditDialog` |
| **No change** | `src/frontend/business.py` | Unchanged |
| **No change** | `src/bridge/models/*.py` | Unchanged |
