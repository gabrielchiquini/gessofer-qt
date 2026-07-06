> **Part of:** [Gessofer-Tauri Documentation](./README.md)

# Build & Deployment

## 8.1 Tauri Build Configuration

**File:** `src-tauri/tauri.conf.json`

```json
{
  "productName": "compras-tauri",
  "version": "0.0.0",
  "identifier": "com.gessofer",
  "build": {
    "beforeDevCommand": "pnpm dev",
    "devUrl": "http://localhost:1420",
    "beforeBuildCommand": "pnpm build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [{
      "title": "compras-tauri",
      "width": 1200,
      "height": 720
    }],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  }
}
```

**Key Settings:**
- **Window:** 1200×720 pixels, titled "compras-tauri"
- **CSP:** Disabled (`null`) — no Content Security Policy
- **Bundle targets:** All platforms (Windows, macOS, Linux)
- **Windows Subsystem:** `windows_subsystem = "windows"` (no console window in release)

## 8.2 Vite Configuration

**File:** `vite.config.ts`

```typescript
export default defineConfig(async () => ({
  plugins: [vue()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: { ignored: ["**/src-tauri/**"] },
  },
  resolve: {
    alias: { "@": path.join(__dirname, "src") },
  },
}));
```

**Key Settings:**
- **Port:** 1420 (fixed, strict)
- **Path alias:** `@/` → `./src/`
- **Ignored watch:** `src-tauri/**` (don't restart Vite on Rust changes)
- **Clear screen:** false (prevents obscuring Rust errors)

## 8.3 Cargo.toml Dependencies

**Production Dependencies:**
| Crate | Version | Purpose |
|-------|---------|---------|
| `tauri` | 2.0.0-beta | Tauri framework |
| `tauri-plugin-shell` | 2.0.0-beta.9 | Shell plugin |
| `sea-orm` | 0.11.0 | ORM (SQLite via sqlx) |
| `serde` | 1.0 | Serialization/deserialization |
| `serde_json` | 1.0 | JSON handling |
| `chrono` | 0.4.23 | Date/time handling |
| `tokio` | 1.25.0 | Async runtime |
| `tracing` | 0.1.37 | Structured logging |
| `tracing-subscriber` | 0.3.16 | Logging subscriber |
| `tracing-appender` | 0.2.3 | File logging |
| `tracing-log` | 0.2.0 | Log compatibility |
| `anyhow` | 1.0.69 | Error handling |
| `unidecode` | 0.3.0 | ASCII normalization |
| `dotenv` | 0.15.0 | Environment variables |
| `hyper-tls` | 0.6 | HTTP client (unused?) |

**Build Dependencies:**
| Crate | Version | Purpose |
|-------|---------|---------|
| `tauri-build` | 2.0.0-beta | Build script helper |
| `dotenv` | 0.15.0 | Environment variables in build |

**Features:**
- `custom-protocol` (default): Enables custom protocol for local file loading
- `e2e`: Enables E2E test mode (different database path)

## 8.4 Frontend Build Pipeline

```
Source (.vue, .ts, .scss)
  ↓
Vite (ESM bundler)
  ↓ (Vue plugin transforms .vue SFCs)
  ↓ (Sass compiler processes .scss)
  ↓ (TypeScript type-checking via vue-tsc)
Bundled Output (ESM modules)
  ↓
dist/ directory
  ↓
Tauri bundles into native executable
```

**Scripts:**
| Script | Command | Description |
|--------|---------|-------------|
| `dev` | `vite` | Development server |
| `build` | `vue-tsc --noEmit && vite build` | Type-check + production build |
| `build-only` | `vite build` | Build without type-checking |
| `type-check` | `vue-tsc --noEmit` | TypeScript type checking |
| `lint` | `eslint . --fix` | ESLint with auto-fix |
| `tauri` | `tauri` | Tauri CLI commands |

**TypeScript Configuration:**
- Target: ES2020
- Module: ESNext (bundler mode)
- Strict mode enabled
- JSX: preserve (for .vue files)
- Path aliases: `@/*` → `./src/*`

## 8.5 E2E Test Configuration

**File:** `wdio.conf.ts`

**Framework:** WebdriverIO v8 with Mocha

**Test Specs:** `./test/specs/**/*.ts`

**Preparation (`onPrepare`):**
1. Clean up any existing temp database files
2. Copy `./src-tauri/main.db` to `%TEMP%\tmp-gessofer-tauri.db`
3. If `SKIP_COMPILE` env var is not set:
   - Run `pnpm build` (frontend build)
   - Run `cargo build --release --features e2e` (Rust build with E2E feature)

**Session Management:**
- Spawns `tauri-driver` process before tests
- Kills `tauri-driver` after tests

**Application Binary:** `./src-tauri/target/release/gessofer-tauri.exe`

**Connection:** Local WebDriver on `127.0.0.1:4444`
