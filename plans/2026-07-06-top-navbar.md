# Implementation Plan: Top Navbar (QMenuBar)

## Summary

This plan describes adding a native Qt top navbar to the Gessofer-Qt QML application. The navbar replaces the original Foundation Sites `<div class="top-bar">` with Qt's `QMenuBar` component, providing dropdown menus for "Notas" and "Despesas" groups with their respective navigation items. The navbar sits at the top of the `ApplicationWindow`, with the existing sidebar + content area below it.

---

## Architecture Overview

### Before (current)

```
ApplicationWindow (main.qml)
└── RowLayout (fill parent)
    ├── Sidebar (left, width: 200px)
    └── WelcomeScreen (right, fills remaining width)
```

### After (with navbar)

```
ApplicationWindow (main.qml)
├── QMenuBar (top, full width)       ← NEW
│   ├── "Notas" (Menu)
│   │   ├── "Pedidos" (MenuItem)
│   │   └── "Cadastrar" (MenuItem)
│   └── "Despesas" (Menu)
│       ├── "Lista" (MenuItem)
│       └── "Cadastrar" (MenuItem)
└── RowLayout (fill remaining height)
    ├── Sidebar (left, width: 200px)
    └── WelcomeScreen (right, fills remaining width)
```

The `QMenuBar` is added as a direct child of `ApplicationWindow` using `MenuBar` from `QtQuick.Controls`. The `RowLayout` is anchored to fill the window *below* the menu bar (i.e., `top` is set to the menu bar's bottom edge, or the layout uses `anchors.fill` with the menu bar as a sibling).

---

## Migration Mapping

### Foundation → QML Component Mapping

| Foundation Element | QML Equivalent | Notes |
|---|---|---|
| `<div class="top-bar">` | `MenuBar` (QtQuick.Controls) | Container for menu items |
| `<ul class="dropdown.menu">` | `Menu` × 2 | One per group ("Notas", "Despesas") |
| `.dropdown-menu` items | `MenuItem` × 4 total | Navigation actions within each menu |
| `.menu-text` ("Notas") | `Menu` title (first line) | The `Menu` header text |
| `<hr class="navbar-divider">` | `MenuBar` bottom border + QSS | QSS `border-bottom` on `MenuBar` |
| `#navbar` | `objectName: "navbar"` | E2E testing ID |
| `#nav-menu-orders` | `objectName: "nav-menu-orders"` | E2E testing ID |
| `#nav-link-orders-list` | `objectName: "nav-link-orders-list"` | E2E testing ID |
| `#nav-link-orders-create` | `objectName: "nav-link-orders-create"` | E2E testing ID |

### E2E Testing ID Mapping

| Original ID | QML `objectName` | Target Component |
|---|---|---|
| `#navbar` | `"navbar"` | Root `MenuBar` |
| `#nav-menu-orders` | `"nav-menu-orders"` | `Menu` "Notas" |
| `#nav-link-orders-list` | `"nav-link-orders-list"` | `MenuItem` "Pedidos" |
| `#nav-link-orders-create` | `"nav-link-orders-create"` | `MenuItem` "Cadastrar" (under Notas) |
| `#nav-menu-expenses` | `"nav-menu-expenses"` | `Menu` "Despesas" |
| `#nav-link-expenses-list` | `"nav-link-expenses-list"` | `MenuItem` "Lista" |
| `#nav-link-expenses-create` | `"nav-link-expenses-create"` | `MenuItem` "Cadastrar" (under Despesas) |

---

## Files to CREATE

### 1. `App/TopNavbar.qml` — The top navbar component

**Path:** `App/TopNavbar.qml`  
**Type:** New file  
**Purpose:** A self-contained `MenuBar` component with two dropdown menus ("Notas" and "Despesas"), populated from `Constants.navGroups`. Includes signals for menu item clicks.

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

pragma ComponentBehavior: Bound

MenuBar {
    id: root

    objectName: "navbar"

    // ── Signals ───────────────────────────────────────
    signal itemClicked(string label, string groupTitle)

    // ── Menu: "Notas" ─────────────────────────────────
    Menu {
        id: notasMenu
        objectName: "nav-menu-orders"
        title: Constants.navGroups[0].title

        Repeater {
            model: Constants.navGroups[0].items

            MenuItem {
                text: modelData.label
                objectName: {
                    if (modelData.label === "Pedidos") return "nav-link-orders-list"
                    if (modelData.label === "Cadastrar") return "nav-link-orders-create"
                    return ""
                }
                onTriggered: root.itemClicked(modelData.label, modelData.group)
            }
        }
    }

    // ── Menu: "Despesas" ──────────────────────────────
    Menu {
        id: despesasMenu
        objectName: "nav-menu-expenses"
        title: Constants.navGroups[1].title

        Repeater {
            model: Constants.navGroups[1].items

            MenuItem {
                text: modelData.label
                objectName: {
                    if (modelData.label === "Lista") return "nav-link-expenses-list"
                    if (modelData.label === "Cadastrar") return "nav-link-expenses-create"
                    return ""
                }
                onTriggered: root.itemClicked(modelData.label, modelData.group)
            }
        }
    }
}
```

**Design rationale:**

- `MenuBar` is the Qt-native component for top-level application navigation with dropdown menus. It is the direct equivalent of Foundation's `.top-bar` with `.dropdown.menu`.
- Each `Menu` uses `objectName` to map to the original Foundation IDs for E2E testing.
- `Repeater` dynamically populates menu items from `Constants.navGroups` — this means the navbar is data-driven, not hardcoded. If `navGroups` changes, the navbar updates automatically.
- The `objectName` binding uses a conditional expression to assign the correct E2E testing ID per item. This is necessary because the original IDs are specific (`nav-link-orders-list`, `nav-link-orders-create`) and not pattern-based.
- The `itemClicked` signal bubbles selection events upward to `main.qml`, matching the existing sidebar click pattern.

---

## Files to MODIFY

### 2. `App/main.qml` — Add navbar to composition root

**Path:** `App/main.qml`  
**Type:** Modify  
**Purpose:** Integrate the `TopNavbar` component at the top of the `ApplicationWindow`, with the existing `RowLayout` (sidebar + content) below it.

**Complete new file contents:**

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

pragma ComponentBehavior: Bound

ApplicationWindow {
    id: root
    visible: true
    width: 1024
    height: 680
    minimumWidth: 800
    minimumHeight: 600
    title: "Gessofer"
    color: Constants.contentBg

    property string selectedItem: "Bem-vindo"
    property string selectedGroup: ""

    TopNavbar {
        width: parent.width
        onItemClicked: {
            root.selectedItem = label
            root.selectedGroup = groupTitle
        }
    }

    RowLayout {
        anchors.top: topBarBottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: 0

        Sidebar {
            Layout.fillHeight: true
            selectedItem: root.selectedItem
            onItemClicked: {
                root.selectedItem = label
                root.selectedGroup = groupTitle
            }
        }

        WelcomeScreen {}
    }

    // Hidden Rectangle to anchor the RowLayout below the menu bar
    // (MenuBar does not participate in layout; this measures its height)
    Rectangle {
        id: topBarBottom
        visible: false
        height: root.contentY + (root.defaultMenuBar ? 0 : 0)
    }
}
```

**Wait — this approach has a problem.** `MenuBar` in QtQuick.Controls does **not** participate in the QML layout system (it does not have a `Layout.preferredHeight`). Anchoring `RowLayout.top` to a fixed offset is fragile.

**Corrected approach — use `Item` spacer or set `Layout.topMargin`:**

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

pragma ComponentBehavior: Bound

ApplicationWindow {
    id: root
    visible: true
    width: 1024
    height: 680
    minimumWidth: 800
    minimumHeight: 600
    title: "Gessofer"
    color: Constants.contentBg

    property string selectedItem: "Bem-vindo"
    property string selectedGroup: ""

    TopNavbar {
        width: parent.width
        onItemClicked: {
            root.selectedItem = label
            root.selectedGroup = groupTitle
        }
    }

    RowLayout {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 0
        spacing: 0

        // The menu bar occupies the top space; set Layout.topMargin
        // to push content below the menu bar height.
        // We use a Binding to dynamically match the menu bar height.
        Layout.topMargin: root.defaultMenuBar ? root.defaultMenuBar.height : 0

        Sidebar {
            Layout.fillHeight: true
            Layout.fillWidth: true
            selectedItem: root.selectedItem
            onItemClicked: {
                root.selectedItem = label
                root.selectedGroup = groupTitle
            }
        }

        WelcomeScreen {}
    }
}
```

**Corrected approach — use a `Frame` wrapper for the menu bar:**

The most reliable approach is to wrap the `MenuBar` in a `Frame` or `Item` with a known preferred height, then anchor the `RowLayout` below it:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

pragma ComponentBehavior: Bound

ApplicationWindow {
    id: root
    visible: true
    width: 1024
    height: 680
    minimumWidth: 800
    minimumHeight: 600
    title: "Gessofer"
    color: Constants.contentBg

    property string selectedItem: "Bem-vindo"
    property string selectedGroup: ""

    // ── Top Navbar ────────────────────────────────────
    Item {
        id: menuBarContainer
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 28

        TopNavbar {
            anchors.fill: parent
            onItemClicked: {
                root.selectedItem = label
                root.selectedGroup = groupTitle
            }
        }
    }

    // ── Main Content Area ─────────────────────────────
    RowLayout {
        anchors.top: menuBarContainer.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: 0

        Sidebar {
            Layout.fillHeight: true
            selectedItem: root.selectedItem
            onItemClicked: {
                root.selectedItem = label
                root.selectedGroup = groupTitle
            }
        }

        WelcomeScreen {}
    }
}
```

**This is the final correct version.** The `Item` spacer with fixed `height: 28` matches the standard menu bar height (28px). The `RowLayout` is anchored to `menuBarContainer.bottom`, ensuring it sits directly below the navbar.

**Changes from the original `main.qml`:**

| Aspect | Before | After |
|---|---|---|
| Menu bar | None | `Item` spacer (28px) + `TopNavbar` at top |
| RowLayout anchors | `anchors.fill: parent` | `anchors.top: menuBarContainer.bottom` + bottom/left/right |
| Sidebar click handler | Existing (unchanged) | Existing (unchanged) |
| Total lines | 18 | ~50 |

---

### 3. `App/qmldir` — Register `TopNavbar` component

**Path:** `App/qmldir`  
**Type:** Modify  
**Purpose:** Register the new `TopNavbar` component in the QML module so `main.qml` can import it via `import "."` (the module system).

**Before:**
```
module App

Main 1.0 main.qml
Sidebar 1.0 Sidebar.qml
WelcomeScreen 1.0 WelcomeScreen.qml
NavigationGroup 1.0 NavigationGroup.qml
NavItem 1.0 NavItem.qml
SidebarHeader 1.0 SidebarHeader.qml
WelcomeIcon 1.0 WelcomeIcon.qml
singleton Constants 1.0 Constants.qml
```

**After:**
```
module App

Main 1.0 main.qml
Sidebar 1.0 Sidebar.qml
WelcomeScreen 1.0 WelcomeScreen.qml
NavigationGroup 1.0 NavigationGroup.qml
NavItem 1.0 NavItem.qml
SidebarHeader 1.0 SidebarHeader.qml
WelcomeIcon 1.0 WelcomeIcon.qml
TopNavbar 1.0 TopNavbar.qml
singleton Constants 1.0 Constants.qml
```

**Change:** Add one line: `TopNavbar 1.0 TopNavbar.qml`

---

## Implementation Order

Execute in this exact sequence to maintain a working state at every step:

### Step 1: Create `App/TopNavbar.qml`

- **Why first:** It is the only new component. It depends only on the existing `Constants` singleton (already in place).
- **Verify:** `qmllint -I . App/TopNavbar.qml` passes with no warnings.

### Step 2: Modify `App/qmldir` — Add `TopNavbar` registration

- **Why second:** The `qmldir` must include the new component before `main.qml` can reference it via the module import.
- **Verify:** `qmllint -I . App/main.qml` passes (confirms module resolution works).

### Step 3: Modify `App/main.qml` — Integrate navbar

- **Why third:** Depends on `TopNavbar.qml` being created and registered.
- **Verify:** 
  1. `qmllint -I . App/main.qml` passes.
  2. Run the application: `python src/main.py`
  3. Confirm the navbar appears at the top with two dropdown menus ("Notas" and "Despesas")
  4. Click each dropdown to verify items are listed correctly
  5. Verify the sidebar and welcome screen still render correctly below the navbar

### Step 4: Apply QSS styling (optional, can be done in parallel with Step 3)

- **Why:** Styling is independent of functionality. The navbar works without custom QSS (uses platform defaults).
- **Verify:** Visual appearance matches the design (dark theme, consistent with sidebar colors).

---

## Styling Approach

### QSS for the Navbar

The project uses QSS (Qt Stylesheets) consistent with the existing color palette. Apply QSS to the `ApplicationWindow` in `main.qml` to style the `MenuBar`:

```qml
ApplicationWindow {
    // ... existing properties ...

    style: Style {
        styleSheet: `
            MenuBar {
                background-color: #1a252f;
                color: #ecf0f1;
                padding: 0px;
                border: none;
            }
            MenuBar::item {
                padding: 4px 12px;
                background-color: transparent;
                color: #ecf0f1;
            }
            MenuBar::item:selected {
                background-color: #34495e;
                color: #ffffff;
            }
            MenuBar::item:pressed {
                background-color: #3498db;
                color: #ffffff;
            }
            Menu {
                background-color: #2c3e50;
                border: 1px solid #34495e;
                color: #ecf0f1;
                padding: 4px;
            }
            Menu::item {
                padding: 6px 32px 6px 12px;
                background-color: transparent;
                color: #ecf0f1;
            }
            Menu::item:selected {
                background-color: #3498db;
                color: #ffffff;
            }
            Menu::item:pressed {
                background-color: #2980b9;
                color: #ffffff;
            }
            Menu::separator {
                height: 1px;
                background: #34495e;
                margin-left: 12px;
                margin-right: 12px;
            }
        `
    }
}
```

**Color mapping from the existing palette:**

| Element | QSS Color | Source |
|---|---|---|
| Menu bar background | `#1a252f` | `Constants.sidebarHeaderBg` |
| Menu bar text | `#ecf0f1` | `Constants.sidebarText` |
| Menu bar hover | `#34495e` | `Constants.sidebarHover` |
| Menu bar pressed | `#3498db` | `Constants.sidebarActive` |
| Menu background | `#2c3e50` | `Constants.sidebarBg` |
| Menu border | `#34495e` | `Constants.sidebarHover` |
| Menu text | `#ecf0f1` | `Constants.sidebarText` |
| Menu item hover | `#3498db` | `Constants.sidebarActive` |
| Menu item pressed | `#2980b9` | Darker shade of `sidebarActive` |
| Separator | `#34495e` | `Constants.sidebarHover` |

**Visual separator below navbar:** The `MenuBar` bottom border (via `border-bottom` in QSS) serves as the equivalent of the original `<hr class="navbar-divider">`. The border color `#34495e` provides a subtle visual division between the navbar and the content area.

### Alternative: Inline QSS via property binding

If QSS in `style` is not preferred, the same styling can be applied via the `style` property on individual `MenuBar`/`Menu`/`MenuItem` components. However, applying it at the `ApplicationWindow` level via `styleSheet` is cleaner and more maintainable.

---

## Risks and Considerations

### 1. `MenuBar` does not participate in QML layout

**Risk:** `MenuBar` in QtQuick.Controls does not report a preferred height to the layout system. Anchoring the `RowLayout` below it requires a fixed-height spacer (`Item` with `height: 28`).

**Mitigation:** The `Item` spacer with `height: 28` is the standard approach. If the menu bar needs dynamic sizing (e.g., multi-line menus), the spacer height should be bound to `topMenuBar.height` via a `Binding` or `onHeightChanged` handler.

### 2. Platform-native menu bar appearance

**Risk:** On Windows, `MenuBar` renders with the native Windows menu bar style. On macOS, it renders as a macOS menu bar. On Linux, it depends on the widget style. The QSS may be partially or fully ignored on some platforms (especially macOS).

**Mitigation:** 
- On Windows/Linux, QSS styling applies fully.
- On macOS, the native menu bar appearance is expected and desirable (it follows platform conventions).
- Document this in the plan so it is known behavior.

### 3. `objectName` on dynamically created `MenuItem` via `Repeater`

**Risk:** `objectName` set in a `Repeater` delegate may not be visible to the QML engine's object tree inspection tools (e.g., `qmlscene --show-objects`).

**Mitigation:** The `objectName` is set via a JavaScript expression in the QML source. It should be visible at runtime to E2E testing tools that query the object tree. Test this explicitly during verification.

### 4. `Repeater` in `Menu` — performance

**Risk:** `Repeater` creates `MenuItem` instances dynamically. With only 2 items per menu (4 total), this is negligible. However, if the menu grows significantly, `Repeater` could cause performance issues.

**Mitigation:** For the current use case (2 groups × 2 items), `Repeater` is appropriate. If menus grow, switch to `ListView` with a `Menu` delegate model.

### 5. `MenuItem` text vs `objectName` conflict for "Cadastrar"

**Risk:** Both "Notas" and "Despesas" menus contain a "Cadastrar" item. The `objectName` distinguishes them (`nav-link-orders-create` vs `nav-link-expenses-create`), but if E2E tests query by text alone, they may match the wrong item.

**Mitigation:** E2E tests should always query by `objectName`, not by text. Document this requirement.

### 6. `onTriggered` signal context in `Repeater` delegate

**Risk:** The `modelData` variable in the `Repeater` delegate is scoped to the delegate instance. If the `Repeater` is destroyed and recreated, the bindings are re-evaluated.

**Mitigation:** This is standard QML behavior and works correctly. The `modelData` variable is always available in a `Repeater` delegate scope.

### 7. `styleSheet` in `style` property vs global stylesheet

**Risk:** Setting `styleSheet` on `ApplicationWindow` via the `style` property may not propagate to all child widgets consistently.

**Mitigation:** Apply the stylesheet at the `QApplication` level in Python (`main.py`) for maximum compatibility. This is the recommended Qt approach for global stylesheets.

---

## Verification Steps

### 1. Lint the new component

```powershell
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . App\TopNavbar.qml
```

Should return exit code 0 (no warnings/errors).

### 2. Lint the modified `main.qml`

```powershell
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . App\main.qml
```

Should return exit code 0.

### 3. Run the application

```powershell
cd C:\Users\gabri\workpace\gessofer-rs\gessofer-qt
python src\main.py
```

### 4. Visual verification checklist

| Check | Expected |
|---|---|
| Navbar appears at the top of the window | Full-width menu bar with "Notas" and "Despesas" headings |
| "Notas" dropdown | Clicking "Notas" shows a dropdown with "Pedidos" and "Cadastrar" |
| "Despesas" dropdown | Clicking "Despesas" shows a dropdown with "Lista" and "Cadastrar" |
| Sidebar still visible | Left sidebar with groups "Notas" and "Despesas" remains unchanged |
| Welcome screen still visible | Content area with welcome icon, title, date, and hint text |
| No overlapping | Navbar does not overlap the sidebar or content area |
| Menu item click → selection | Clicking a menu item updates `selectedItem` (same behavior as sidebar click) |

### 5. E2E testing ID verification

Verify that the `objectName` properties are set correctly on the runtime objects:

| ID | Component | `objectName` value |
|---|---|---|
| `#navbar` | `MenuBar` | `"navbar"` |
| `#nav-menu-orders` | `Menu` "Notas" | `"nav-menu-orders"` |
| `#nav-menu-expenses` | `Menu` "Despesas" | `"nav-menu-expenses"` |
| `#nav-link-orders-list` | `MenuItem` "Pedidos" | `"nav-link-orders-list"` |
| `#nav-link-orders-create` | `MenuItem` "Cadastrar" (Notas) | `"nav-link-orders-create"` |
| `#nav-link-expenses-list` | `MenuItem` "Lista" | `"nav-link-expenses-list"` |
| `#nav-link-expenses-create` | `MenuItem` "Cadastrar" (Despesas) | `"nav-link-expenses-create"` |

### 6. Styling verification

| Check | Expected |
|---|---|
| Menu bar background color | `#1a252f` (dark blue-gray, matches sidebar header) |
| Menu bar text color | `#ecf0f1` (light, matches sidebar text) |
| Menu background | `#2c3e50` (dark blue-gray, matches sidebar bg) |
| Menu item hover | `#3498db` (blue, matches sidebar active) |
| Visual separator below navbar | Subtle border at `#34495e` |
| Consistency with sidebar | Colors match the existing sidebar palette |

---

## Summary of File Changes

| Action | File | Lines (approx) | Dependencies |
|--------|------|-----------------|--------------|
| CREATE | `App/TopNavbar.qml` | ~50 | `Constants` |
| MODIFY | `App/qmldir` | +1 line | None |
| MODIFY | `App/main.qml` | 18 → ~50 | `TopNavbar` |

**Total new code:** ~50 lines in 1 new file  
**Net change:** +32 lines (net), +1 file

---

## Appendix: Alternative Approaches Considered

### A. `QToolBar` instead of `QMenuBar`

**Rejected because:** `QToolBar` is designed for tool buttons and action bars, not dropdown navigation menus. `QMenuBar` is the correct Qt pattern for application-level navigation with dropdown menus, matching the original Foundation `.top-bar` + `.dropdown.menu` pattern exactly.

### B. Custom QML `RowLayout` with `Button` + `Popup` instead of `MenuBar` + `Menu`

**Rejected because:** This would reinvent the wheel. `QMenuBar` and `QMenu` provide native dropdown behavior, keyboard navigation (Alt+letter), and platform-native rendering. A custom implementation would be more complex and less polished.

### C. Python-side `QMenuBar` (not QML)

**Rejected because:** The project uses QML for all UI components. Mixing Python-side `QMenuBar` with QML content would create inconsistency and complicate styling. The `QtQuick.Controls` `MenuBar` provides the same functionality entirely in QML.

### D. `MenuBar` with hardcoded `MenuItem` elements instead of `Repeater`

**Considered:** Hardcoding 4 `MenuItem` elements would be simpler but less maintainable. Using `Repeater` with `Constants.navGroups` makes the navbar data-driven — if the navigation structure changes, only `Constants.qml` needs to be updated.
