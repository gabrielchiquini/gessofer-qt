# Implementation Plan: Refactor main.qml into Modular QML Components

## Summary

This plan describes the step-by-step refactoring of `main.qml` from a 253-line monolithic component into a clean, modular architecture of 7 QML files. The refactoring eliminates deeply nested `root.` qualified access (the cause of the `UnqualifiedAccess` linter warning), replaces it with property bindings and signals, and introduces a QML singleton for shared constants. The final `main.qml` becomes a ~25-line composition root.

---

## Architecture Overview

```
main.qml                        ← Composition root (~25 lines)
  ├── Constants.qml     ← Singleton: all shared constants
  ├── Sidebar.qml               ← Sidebar container (header + nav)
  │   ├── SidebarHeader.qml     ← "Gessofer" title bar
  │   └── NavigationGroup.qml   ← One group (title + items)
  │       └── NavItem.qml       ← One clickable nav item
  └── WelcomeScreen.qml         ← Welcome/content area
      └── WelcomeIcon.qml       ← Decorative "G" icon
```

### Communication Pattern

| Direction | Mechanism |
|-----------|-----------|
| Parent → Child | QML property bindings (e.g., `selectedItem: root.selectedItem`) |
| Child → Parent | Signal (`itemClicked`) with bubbling via handler |

### Import Mechanism for Singleton

All components import the singleton via:
```qml
 1.0
```

The `qmldir` file in the project root declares `module gessofer` and registers `Constants` as a `singleton`. Qt's QML engine resolves ` 1.0` by finding the `qmldir` file. The `singleton` directive tells the engine that `Constants` is a singleton type — it can be accessed directly as `Constants.propertyName` without instantiation.

**No Python-side `qmlRegisterSingletonType` needed.** The `qmldir` + `pragma Singleton` combination is the standard QML module system. The Python `main.py` continues to load `main.qml` exactly as before — no changes to the Python side.

---

## Files to CREATE

### 1. `Constants.qml` — QML Singleton with all shared constants

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\Constants.qml`  
**Type:** New file  
**Purpose:** Centralized constants (colors, dimensions, navigation data, welcome text) accessible from any component.

**Complete file contents:**

```qml
pragma Singleton
import QtQuick

QtObject {
    id: constants

    // ── Dimensions ──────────────────────────────────────
    readonly property int sidebarWidth: 200
    readonly property int sidebarHeaderHeight: 56
    readonly property int navItemHeight: 40
    readonly property int contentMargins: 40

    // ── Colors ──────────────────────────────────────────
    readonly property string sidebarBg: "#2c3e50"
    readonly property string sidebarText: "#ecf0f1"
    readonly property string sidebarHover: "#34495e"
    readonly property string sidebarActive: "#3498db"
    readonly property string sidebarHeaderBg: "#1a252f"
    readonly property string contentBg: "#ecf0f1"
    readonly property string accentColor: "#3498db"
    readonly property string indicatorColor: "#ffffff"
    readonly property string separatorColor: "#bdc3c7"
    readonly property string metaTextColor: "#95a5a6"
    readonly property string hintTextColor: "#bdc3c7"

    // ── Navigation ──────────────────────────────────────
    readonly property var navGroups: [
        {
            title: "Notas",
            items: [
                { label: "Pedidos", group: "Notas" },
                { label: "Cadastrar", group: "Notas" }
            ]
        },
        {
            title: "Despesas",
            items: [
                { label: "Lista", group: "Despesas" },
                { label: "Cadastrar", group: "Despesas" }
            ]
        }
    ]

    // ── Welcome text ────────────────────────────────────
    readonly property string welcomeTitle: "Bem-vindo ao Gessofer"
    readonly property string welcomeSubtitle: "Sistema de Gest\u00e3o de Pedidos e Despesas"
    readonly property string welcomeHint: "Selecione uma op\u00e7\u00e3o no menu lateral para come\u00e7ar"
    readonly property string welcomeLetter: "G"
}
```

**Why this structure:** `QtObject` is the base type for non-visual singleton containers. It has no visual presence, no size, no rendering cost. The `id: constants` allows dot-access to properties. All properties are `readonly` to enforce immutability — they are configuration, not state.

---

### 2. `Sidebar.qml` — Sidebar container

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\Sidebar.qml`  
**Type:** New file  
**Purpose:** The left sidebar that holds the header and navigation. It is a visual component that occupies the left side of the window.

**Complete file contents:**

```qml
import QtQuick
import QtQuick.Layouts
 1.0

Rectangle {
    id: sidebar

    anchors.left: parent.left
    anchors.top: parent.top
    anchors.bottom: parent.bottom
    width: Constants.sidebarWidth
    color: Constants.sidebarBg

    property string selectedItem: ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 0

        SidebarHeader {}

        Repeater {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: Constants.navGroups

            NavigationGroup {
                group: modelData
                selectedItem: sidebar.selectedItem
                onItemClicked: {
                    sidebar.selectedItem = label
                }
            }
        }
    }
}
```

**Why this structure:**
- `selectedItem` is a **mutable property** on the Sidebar (not readonly) so it can be updated from within.
- The `Repeater` delegate passes `modelData` (the current group object) as the `group` property to `NavigationGroup`.
- The `onItemClicked` handler updates `sidebar.selectedItem` locally. This property is then bound downward to child components.
- No `root.` references anywhere — only `Constants.` and `sidebar.` (self-reference).
- The `selectedItem` property is exposed so `main.qml` can bind its own state into this component.

---

### 3. `SidebarHeader.qml` — The "Gessofer" title bar

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\SidebarHeader.qml`  
**Type:** New file  
**Purpose:** The dark header bar at the top of the sidebar showing the app name.

**Complete file contents:**

```qml
import QtQuick
 1.0

Rectangle {
    Layout.fillWidth: true
    Layout.preferredHeight: Constants.sidebarHeaderHeight
    color: Constants.sidebarHeaderBg

    Text {
        anchors.centerIn: parent
        text: "Gessofer"
        font.bold: true
        font.pixelSize: 20
        color: Constants.indicatorColor
    }
}
```

**Why this structure:** A minimal, self-contained component. Uses `Layout.fillWidth` and `Layout.preferredHeight` to participate in the `ColumnLayout` parent. No properties, no signals — pure presentation.

---

### 4. `NavigationGroup.qml` — One navigation group

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\NavigationGroup.qml`  
**Type:** New file  
**Purpose:** Renders a single group's title and its list of navigation items. This replaces the outer `Repeater` delegate from the original monolith.

**Complete file contents:**

```qml
import QtQuick
import QtQuick.Layouts
 1.0

Column {
    id: groupContainer

    property var group: null
    property string selectedItem: ""

    signal itemClicked(string label, string groupTitle)

    width: parent ? parent.width : Constants.sidebarWidth

    // Group title
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: 16
        color: "transparent"

        Text {
            anchors.fill: parent
            text: group.title
            font.bold: true
            font.pixelSize: 11
            font.capitalization: Font.Capitalize
            color: Constants.metaTextColor
            verticalAlignment: Text.AlignTop
            elide: Text.ElideRight
        }
    }

    // Group items
    Repeater {
        model: group.items

        NavItem {
            itemLabel: modelData.label
            itemGroup: modelData.group
            selectedItem: groupContainer.selectedItem
            onItemClicked: {
                groupContainer.itemClicked(label, groupTitle)
            }
        }
    }
}
```

**Why this structure:**
- `group` is a `var` property holding the group data object (title + items array).
- `itemClicked(label, groupTitle)` signal bubbles clicks upward to `Sidebar.qml`.
- The inner `Repeater` delegate accesses `modelData` directly from its own scope — this is the standard, linter-approved pattern. The `UnqualifiedAccess` warning only triggers when accessing an **outer-scope ID** (like `root.selectedItem`) from deep nesting. Accessing `modelData` from a Repeater delegate is valid QML.
- Each `NavItem` receives its data via explicit property bindings (`itemLabel`, `itemGroup`), not by reaching up to a parent ID.

---

### 5. `NavItem.qml` — One clickable navigation item

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\NavItem.qml`  
**Type:** New file  
**Purpose:** A single navigation item with background, label, active indicator, and MouseArea. This was the deepest nesting level (4+ levels) in the original monolith.

**Complete file contents:**

```qml
import QtQuick
 1.0

Rectangle {
    id: itemRect

    width: parent ? parent.width : Constants.sidebarWidth
    height: Constants.navItemHeight

    property string itemLabel: ""
    property string itemGroup: ""
    property string selectedItem: ""

    readonly property bool isActive: selectedItem === itemLabel

    signal itemClicked(string label, string groupTitle)

    color: {
        if (isActive) {
            return Constants.sidebarActive;
        }
        if (mouseArea.containsPress) {
            return Constants.sidebarHover;
        }
        return "transparent";
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton

        onClicked: {
            itemClicked(itemLabel, itemGroup)
        }
    }

    Text {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        leftPadding: 16
        text: itemLabel
        font.pixelSize: 13
        color: isActive ? Constants.indicatorColor : Constants.sidebarText
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: isActive ? 3 : 0
        color: Constants.indicatorColor
    }
}
```

**Why this structure:**
- **Critical fix:** The original code referenced `root.selectedItem` from 4 levels of nesting. This component now receives `selectedItem` as a property binding from its parent (`NavigationGroup` → `Sidebar` → `main.qml`). No outer-scope ID access.
- `isActive` is a `readonly` computed property — it's a binding, not a signal handler, so it re-evaluates automatically when `selectedItem` changes.
- The `itemClicked` signal carries both `label` and `groupTitle` so the caller knows exactly what was selected.
- All colors come from `Constants.` — no hardcoded color strings.
- The `Rectangle` with `id: itemRect` is used internally only; it is not accessed from any outer scope.

---

### 6. `WelcomeScreen.qml` — The welcome/content area

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\WelcomeScreen.qml`  
**Type:** New file  
**Purpose:** The right-side content area showing the welcome screen with decorative icon, title, subtitle, separator, date, and hint text.

**Complete file contents:**

```qml
import QtQuick
import QtQuick.Layouts
 1.0

Rectangle {
    id: contentArea

    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.bottom: parent.bottom

    color: Constants.contentBg

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Constants.contentMargins
        spacing: 16

        WelcomeIcon {}

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Constants.welcomeTitle
            font.bold: true
            font.pixelSize: 28
            color: Constants.sidebarBg
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Constants.welcomeSubtitle
            font.pixelSize: 16
            color: Constants.metaTextColor
        }

        Rectangle {
            Layout.preferredWidth: 120
            Layout.preferredHeight: 2
            Layout.alignment: Qt.AlignHCenter
            color: Constants.separatorColor
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatDateTime(new Date(), "dddd, dd 'de' MMMM 'de' yyyy ' \u00e0s' HH:mm")
            font.pixelSize: 14
            color: Constants.metaTextColor
        }

        Item { Layout.fillHeight: true }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Constants.welcomeHint
            font.pixelSize: 13
            color: Constants.hintTextColor
        }
    }
}
```

**Why this structure:**
- Replaces the entire `Rectangle` content area from the original monolith (lines 177–251).
- All text content and colors come from `Constants.` — no hardcoded strings or colors.
- The `WelcomeIcon` is a separate component for clarity.
- No signals, no properties — purely presentational.

---

### 7. `WelcomeIcon.qml` — The decorative "G" icon

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\WelcomeIcon.qml`  
**Type:** New file  
**Purpose:** The large circular "G" icon at the top of the welcome screen.

**Complete file contents:**

```qml
import QtQuick
 1.0

Rectangle {
    Layout.preferredWidth: 80
    Layout.preferredHeight: 80
    Layout.alignment: Qt.AlignHCenter
    radius: 40
    color: Constants.accentColor

    Text {
        anchors.centerIn: parent
        text: Constants.welcomeLetter
        font.bold: true
        font.pixelSize: 36
        color: Constants.indicatorColor
    }
}
```

**Why this structure:** A single-paragraph component. The `radius: 40` on an 80×80 rectangle creates a perfect circle. All values come from constants.

---

### 0. `qmldir` — QML module declaration

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\qmldir`  
**Type:** New file  
**Purpose:** Declares the current directory as a QML module named `gessofer` and registers `Constants` as a singleton.

**Complete file contents:**

```
module gessofer
singleton Constants Constants.qml
```

**Why this is needed:** The `import "." 1.0` approach (importing the current directory as a module) is not reliably supported by qmllint or by all Qt 6.x engine configurations. A `qmldir` file is the standard, documented way to register a QML module. With this file, all components can import the singleton reliably via ` 1.0`.

---

## Files to MODIFY

### 8. `main.qml` — Composition root

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\main.qml`  
**Type:** Modify (replace entire contents)  
**Purpose:** The application window that composes the sidebar and content area. Reduced from 253 lines to ~25 lines.

**Complete file contents:**

```qml
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
 1.0

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

    RowLayout {
        anchors.fill: parent
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

**What changed and why:**

| Aspect | Before | After |
|--------|--------|-------|
| Sidebar layout | Nested `Rectangle` with `anchors` inside a parent `Rectangle` | `Sidebar` component in `RowLayout` |
| Content area layout | Nested `Rectangle` with `anchors` | `WelcomeScreen` component in `RowLayout` |
| Constants | 15+ properties on `root` | All in `Constants` singleton |
| Selection state | `selectedItem` and `selectedGroup` on `root` (accessed from deep nesting) | Same properties on `root`, but only `Sidebar` writes to them via signal handler |
| `root.` access from children | 12+ occurrences from 4+ nesting levels | **Zero** — all children use property bindings and `Constants.` |
| Total lines | 253 | ~25 |

**Rationale for `RowLayout`:** This exactly replicates the original side-by-side layout (sidebar left, content right). `Sidebar` already manages its own width via `Constants.sidebarWidth`. `WelcomeScreen` fills the remaining space. `Layout.fillHeight: true` ensures both fill the window height.

> **Note:** `Sidebar`'s internal `anchors.left` is overridden by `RowLayout` positioning. This is expected and correct — `RowLayout` places `Sidebar` at the left edge automatically. The `width` is determined by `Sidebar`'s internal `Rectangle` which sets `width: Constants.sidebarWidth`.

---

### 9. `.qmllint.ini` — Remove UnqualifiedAccess suppression

**Path:** `C:\Users\gabri\workpace\gessofer-rs\gessofer-qt\.qmllint.ini`  
**Type:** Modify  
**Purpose:** Remove the `UnqualifiedAccess=disable` line since the refactoring eliminates the root cause.

**Change needed:**

Remove line 4:
```
UnqualifiedAccess=disable
```

The rest of the file remains unchanged.

**Before (lines 1-7):**
```ini
[Rules]

[Warnings]
UnqualifiedAccess=disable
ConfusingExpressionStatement=warning
ImportFailure=warning
```

**After (lines 1-7):**
```ini
[Rules]

[Warnings]
ConfusingExpressionStatement=warning
ImportFailure=warning
```

**Why this is safe:** The `UnqualifiedAccess` warning in qmllint triggers when a QML component accesses an `id` from an outer (enclosing) scope without qualifying it. In the original `main.qml`, the deeply nested Repeater delegates accessed `root.selectedItem`, `root.sidebarWidth`, `root.sidebarBg`, etc. — all from 4+ levels of nesting. After the refactoring:

1. **`Constants.qml`** — No outer-scope access needed. It defines constants.
2. **`Sidebar.qml`** — Only accesses `Constants.` (singleton, always in scope) and `sidebar.` (self-reference, always allowed).
3. **`SidebarHeader.qml`** — Only accesses `Constants.` and `Layout.` (attached property, always in scope).
4. **`NavigationGroup.qml`** — Accesses `Constants.`, `group.` (its own property), and `modelData` (Repeater delegate's implicit variable — this is **not** an unqualified access to an outer scope ID; it is a built-in Repeater feature). The `onItemClicked` handler accesses `label` and `groupTitle` which are parameters of the signal handler — also not unqualified access.
5. **`NavItem.qml`** — Only accesses `Constants.`, `mouseArea` (its own `id`), `itemLabel`, `itemGroup`, `selectedItem` (its own properties), and `isActive` (its own computed property). **Zero outer-scope ID access.**
6. **`WelcomeScreen.qml`** — Only accesses `Constants.` and `Qt.` (built-in).
7. **`WelcomeIcon.qml`** — Only accesses `Constants.` and `Layout.`.
8. **`main.qml`** — Only accesses `root.` (self-reference) and component properties via explicit bindings.

The `modelData` variable accessed in Repeater delegates is a **built-in implicit variable** provided by the Repeater itself — it is not an unqualified access to an enclosing scope's `id`. This has always been valid QML and never triggered the `UnqualifiedAccess` warning.

---

## Implementation Order

Execute in this exact sequence to maintain a working state at every step:

### Step 0: Create `qmldir`
- **Why first:** All other components depend on it for the ` 1.0` statement.
- **Verify:** `qmllint -I . Constants.qml` passes with no `ImportFailure` warnings.

### Step 1: Create `Constants.qml`
- **Why first:** All other components depend on it. It has no dependencies.
- **Verify:** `qmllint Constants.qml` passes with no warnings.

### Step 2: Create `SidebarHeader.qml`
- **Why second:** Simplest component, only depends on `Constants`.
- **Verify:** `qmllint SidebarHeader.qml` passes.

### Step 3: Create `NavItem.qml`
- **Why third:** The most critical component (was the deepest nesting). Self-contained, only depends on `Constants`.
- **Verify:** `qmllint NavItem.qml` passes.

### Step 4: Create `NavigationGroup.qml`
- **Why fourth:** Depends on `Constants` and `NavItem.qml` (created in Step 3).
- **Verify:** `qmllint NavigationGroup.qml` passes.

### Step 5: Create `Sidebar.qml`
- **Why fifth:** Depends on `Constants`, `SidebarHeader.qml`, and `NavigationGroup.qml` (all created).
- **Verify:** `qmllint Sidebar.qml` passes.

### Step 6: Create `WelcomeIcon.qml`
- **Why sixth:** Simple, only depends on `Constants`.
- **Verify:** `qmllint WelcomeIcon.qml` passes.

### Step 7: Create `WelcomeScreen.qml`
- **Why seventh:** Depends on `Constants` and `WelcomeIcon.qml`.
- **Verify:** `qmllint WelcomeScreen.qml` passes.

### Step 8: Rewrite `main.qml`
- **Why eighth:** Depends on all components above. This is the composition root.
- **Verify:** `qmllint main.qml` passes.

### Step 9: Update `.qmllint.ini`
- **Why last:** Removes the suppression that was hiding the original problem.
- **Verify:** Run `qmllint` on all `.qml` files — all should pass cleanly.

---

## How the Singleton Is Imported

### Import statement used in each file:

All component files use:
```qml
 1.0
```

### How it works:

1. The `qmldir` file in the project root declares `module gessofer` and registers `Constants` as a `singleton`.
2. Qt's QML engine resolves ` 1.0` by finding the `qmldir` file in the directory of the importing file (or any directory in the QML import path).
3. The `singleton` directive tells the engine that `Constants` is a singleton type — it can be accessed directly as `Constants.propertyName` without instantiation.
4. All properties are accessed as `Constants.someProperty` (e.g., `Constants.sidebarBg`).

**No Python-side `qmlRegisterSingletonType` needed.** The `qmldir` + `pragma Singleton` combination is the standard QML module system. The Python `main.py` continues to load `main.qml` exactly as before — no changes to the Python side.

---

## How qmllint Will Be Clean

### The `UnqualifiedAccess` warning explained

The qmllint `UnqualifiedAccess` warning fires when a QML component accesses an `id` that belongs to an **enclosing scope** without proper qualification. In the original `main.qml`:

```qml
// Line 127-128: 4 levels of nesting deep
if (root.selectedItem === modelData.label) {
    return root.sidebarActive;   // root is from the ApplicationWindow, 4+ levels up
}
```

This is `UnqualifiedAccess` because `root` is an `id` defined on the `ApplicationWindow` (the root), and it is being accessed from a `Rectangle` inside a `Repeater` inside another `Repeater` inside a `Column` inside a `ColumnLayout` inside a `Rectangle` inside the `ApplicationWindow`.

### How the refactoring eliminates it

| Original pattern | New pattern | Why it's clean |
|-----------------|-------------|----------------|
| `root.sidebarBg` | `Constants.sidebarBg` | `Constants` is a singleton type imported at the top of each file — it's in scope, not an outer-scope ID |
| `root.selectedItem` (from NavItem) | `selectedItem` (property binding) | `selectedItem` is a **property of the component itself**, not an outer-scope ID |
| `root.sidebarWidth` | `Constants.sidebarWidth` | Same singleton pattern |
| `root.metaTextColor` | `Constants.metaTextColor` | Same singleton pattern |
| `root.indicatorColor` | `Constants.indicatorColor` | Same singleton pattern |
| `root.sidebarHeaderBg` | `Constants.sidebarHeaderBg` | Same singleton pattern |
| `root.contentBg` | `Constants.contentBg` | Same singleton pattern |
| `root.accentColor` | `Constants.accentColor` | Same singleton pattern |
| `root.separatorColor` | `Constants.separatorColor` | Same singleton pattern |
| `root.hintTextColor` | `Constants.hintTextColor` | Same singleton pattern |

The only `root.` references remaining are in `main.qml` itself, where `root` is the **self-reference** of the `ApplicationWindow` — this is always allowed and never triggers `UnqualifiedAccess`.

### Files that previously needed suppression and why they won't now

| File | Was suppressed | Now |
|------|---------------|-----|
| `main.qml` | Had `UnqualifiedAccess=disable` | No outer-scope ID access from nested components |
| All component files | N/A (didn't exist) | Each file is self-contained with no outer-scope dependencies |

---

## Verification Steps

### 1. Lint all QML files individually

```powershell
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . Constants.qml
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . SidebarHeader.qml
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . NavItem.qml
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . NavigationGroup.qml
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . Sidebar.qml
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . WelcomeIcon.qml
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . WelcomeScreen.qml
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . main.qml
```

All should return exit code 0 (no warnings/errors).

### 2. Lint the entire directory at once

```powershell
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . *.qml
```

This checks all `.qml` files in the current directory with the current directory as the QML import path (needed so `qmldir` is found).

### 3. Lint with the project's `.qmllint.ini` settings

```powershell
& "C:\Users\gabri\miniconda3\envs\gessofer-qt\Lib\site-packages\PySide6\qmllint.exe" -I . *.qml
```

This uses the `.qmllint.ini` configuration. After removing `UnqualifiedAccess=disable`, this should still pass because no file has unqualified access violations.

### 4. Run the application

```powershell
cd C:\Users\gabri\workpace\gessofer-rs\gessofer-qt
python main.py
```

The application should:
- Launch with the same visual appearance as before (sidebar on left, welcome screen on right)
- Display "Gessofer" in the sidebar header
- Show navigation groups "Notas" and "Despesas" with their items
- Show the welcome screen with the "G" icon, title, subtitle, date, and hint text
- Clicking a navigation item should update the selection (no visual change yet since WelcomeScreen doesn't react to selection, but the state is tracked)

### 5. Verify the visual appearance matches

Compare the refactored app side-by-side with the original (if the original is still available as a backup). The key visual elements to verify:

- Sidebar background: `#2c3e50` (dark blue-gray)
- Sidebar header: `#1a252f` (darker blue-gray)
- Active nav item: `#3498db` (blue highlight)
- Nav item text: `#ecf0f1` (light)
- Active nav item text: `#ffffff` (white)
- Active indicator bar: 3px wide, white, on the left edge
- Content background: `#ecf0f1` (light gray)
- Welcome icon: 80×80 circle, `#3498db` blue
- Date/time text: `#95a5a6` (medium gray)
- Hint text: `#bdc3c7` (light gray)

### 6. Verify Python side is unchanged

```powershell
# Confirm main.py has not been modified
# (It should not need changes)
```

---

## Risks and Considerations

### 1. `qmldir` module resolution
**Risk:** qmllint must be invoked with `-I .` to find the `qmldir` file.  
**Mitigation:** Always run qmllint with `-I .` flag: `qmllint -I . *.qml`. This tells qmllint to use the current directory as the QML import path where it will find `qmldir`.

### 2. `pragma ComponentBehavior: Bound` in main.qml
**Risk:** This pragma was on the original `main.qml`. It is retained but may not be strictly necessary after the refactoring.  
**Decision:** Keep it for now to minimize changes. It can be removed in a follow-up if it causes issues or is confirmed unnecessary.

### 3. `modelData` in Repeater delegates
**Risk:** None. `modelData` is a built-in Repeater implicit variable, not an unqualified access to an outer-scope ID. This has always been valid QML.

### 4. Layout changes
**Risk:** The original used `Rectangle` with `anchors` for the side-by-side layout. The new version uses `RowLayout`.  
**Mitigation:** `RowLayout` with `Layout.fillHeight: true` on `Sidebar` and no explicit width on `WelcomeScreen` produces the same visual result: sidebar takes its preferred width (200px), content fills the rest.

### 5. Date formatting
**Risk:** The date formatting uses `Qt.formatDateTime` with Portuguese locale strings (`"dddd, dd 'de' MMMM 'de' yyyy ' \u00e0s' HH:mm"`).  
**Mitigation:** This was preserved exactly as-is in `WelcomeScreen.qml`. No change.

### 6. Unicode escape sequences
**Risk:** The original used `\u00e3` (ã) and `\u00e7` (ç) escape sequences.  
**Mitigation:** These are preserved in `Constants.qml` as `\u00e3` and `\u00e7` in the `welcomeSubtitle` and `welcomeHint` properties.

### 7. No `qmlRegisterSingletonType` in Python
**Risk:** The original Python code did not register any QML types.  
**Mitigation:** The `qmldir` + `pragma Singleton` approach is fully self-contained in QML and does not require Python changes.

---

## Summary of File Changes

| Action | File | Lines (approx) | Dependencies |
|--------|------|-----------------|--------------|
| CREATE | `qmldir` | 2 | None |
| CREATE | `Constants.qml` | 55 | None |
| CREATE | `SidebarHeader.qml` | 14 | `Constants` |
| CREATE | `NavItem.qml` | 42 | `Constants` |
| CREATE | `NavigationGroup.qml` | 38 | `Constants`, `NavItem` |
| CREATE | `Sidebar.qml` | 30 | `Constants`, `SidebarHeader`, `NavigationGroup` |
| CREATE | `WelcomeIcon.qml` | 14 | `Constants` |
| CREATE | `WelcomeScreen.qml` | 55 | `Constants`, `WelcomeIcon` |
| MODIFY | `main.qml` | 25 → ~25 | All components above |
| MODIFY | `.qmllint.ini` | Remove 1 line | N/A |

**Total new code:** ~250 lines across 8 files (was 253 lines in 1 file)  
**Net change:** +7 lines, but with dramatically improved maintainability, testability, and linter compliance.
