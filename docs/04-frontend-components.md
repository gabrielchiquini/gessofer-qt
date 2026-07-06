> **Part of:** [Gessofer-Tauri Documentation](./README.md)

# Frontend — Components

## 4.1 AppNavbar

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

## 4.2 DataTable

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

## 4.3 FormInput

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

## 4.4 MonthQueryForm

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

## 4.5 AlertContainer

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

## 4.6 MessageContainer

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

## 4.7 FoundationTooltip

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

## 4.8 ExpensesTable

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
