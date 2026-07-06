# Gessofer-Tauri — Application Documentation

> **Purpose:** This document provides a complete, exhaustive specification of the Gessofer-Tauri application, enabling developers to implement a full rewrite in Python + PySide6 without needing to reference the original source code.

> **Version:** Current application version is `0.0.0`. Built with Tauri 2 (beta), Vue 3, TypeScript, and SQLite via SeaORM.

---

## Table of Contents

| # | File | Description |
|---|------|-------------|
| 1 | [Application Overview & Business Context](./01-overview.md) | High-level purpose, user roles, glossary of Brazilian business terms, data currency format convention |
| 2 | [Database Schema & Data Model](./02-database.md) | Complete current and legacy SQLite schemas, entity relationships, migration strategy, database file locations, field naming conventions |
| 3 | [Frontend — Views & Screens](./03-frontend-views.md) | ProductList, OrderEdit (the most complex screen), ExpensesView, ExpensesEdit, AboutView, navigation and routing map |
| 4 | [Frontend — Components](./04-frontend-components.md) | AppNavbar, DataTable, FormInput, MonthQueryForm, AlertContainer, MessageContainer, FoundationTooltip, ExpensesTable |
| 5 | [Frontend — Utilities & Shared Logic](./05-utilities.md) | Date utilities (Luxon), currency utilities, Yup/vee-validate validation extensions, NFe XML parser, ID generator, Pinia state management |
| 6 | [Backend — Rust/Tauri Architecture](./06-backend.md) | Tauri 2 app structure, Tauri commands API surface, API layer architecture, database repository layer, error handling, logging, AppData shared state |
| 7 | [Styling & UI Framework](./07-styling.md) | Foundation Sites integration, CSS architecture, font usage, FontAwesome icon system, input masking, responsive layout patterns |
| 8 | [Build & Deployment](./08-build-deployment.md) | Tauri build configuration, Vite configuration, Cargo.toml dependencies, frontend build pipeline, E2E test configuration |
| 9 | [Testing](./09-testing.md) | E2E test suite structure, test scenarios, test helpers |
| 10 | [Migration Mapping (for Python Port)](./10-migration-mapping.md) | Vue → PySide6, Pinia → PyQt, Tauri → Python backend, SeaORM → SQLite, Yup → Python validation, Foundation → Qt, Luxon → datetime, Inputmask → Qt |
| 11 | [Appendix A + B](./11-appendix.md) | Complete file index (frontend, backend, configuration) and business rules summary |

---
