> **Part of:** [Gessofer-Tauri Documentation](./README.md)

# Styling & UI Framework

## 7.1 Foundation Sites Integration

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

## 7.2 CSS Architecture

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

## 7.3 Font Usage

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

## 7.4 Icon System

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

## 7.5 Input Masking System

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

## 7.6 Responsive Layout Patterns

**Grid System:** Foundation's responsive grid with breakpoint-based classes:
- `cell shrink` — Content-sized cells
- `cell auto` — Fluid-width cells
- `cell small-3` — 3 columns on small screens and up
- `cell medium-1`, `medium-2`, `medium-3`, `medium-6`, `medium-9` — Responsive column widths
- `grid-x grid-margin-x` — Grid with margins between cells
- `align-justify`, `align-right`, `align-middle` — Alignment utilities
