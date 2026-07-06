> **Part of:** [Gessofer-Tauri Documentation](./README.md)

# Application Overview & Business Context

## 1.1 High-Level Purpose

Gessofer-Tauri is a **purchasing and order management desktop application** for **Gessofer**, a Brazilian building materials supplier (likely specializing in gypsum/plaster products, given the name "Gessofer"). The application manages:

- **Purchase orders (Notas Fiscais / NFe):** Recording incoming supplier invoices with line-item products, prices, freight (transportation) costs, and unloading costs.
- **Product price tracking:** A searchable, filterable, paginated list of all products purchased across orders.
- **Operating expenses (Despesas):** Monthly expense tracking for business overhead.
- **NFe XML import:** Automatic parsing of Brazilian electronic invoice XML files to pre-populate order data.

The application runs as a **desktop app** using Tauri (Rust backend + web frontend), packaged as a Windows installer via WiX.

## 1.2 User Roles and Target Users

| Role | Description |
|------|-------------|
| **Purchase Manager / Buyer** | Primary user. Creates/edit purchase orders, imports NFe XMLs, distributes freight costs across products, and tracks expenses. |
| **Administrator** | Manages the database, runs migrations, and oversees the application. |

There is **no authentication system** — the application assumes a single trusted user operating locally on a Windows machine.

## 1.3 Glossary of Brazilian Business Terms

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

## 1.4 Data Currency Format Convention

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
