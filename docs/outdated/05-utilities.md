> **Part of:** [Gessofer-Tauri Documentation](README.md)

# Frontend — Utilities & Shared Logic

## 5.1 Date Utilities

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

## 5.2 Currency Utilities

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

## 5.3 Validation Extensions

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

## 5.4 NFe XML Parser

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

## 5.5 ID Generator

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

## 5.6 State Management

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
