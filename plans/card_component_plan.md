# Implementation Plan: New `Card` PySide6 Component

## Summary
Create a reusable, highly stylized `Card` widget using PySide6 that serves as a structural container for other UI elements. The card will feature a header, a main content area, and a footer, separated by thin horizontal lines, following the existing design language of the application.

## Files to Create
- **Path:** `src/frontend/components/card.py`
- **Purpose:** Defines the `Card` widget class.
- **Key contents:** 
    - `Card(QFrame)` class.
    - `set_title(text: str) -> None`
    - `set_content(widget: QWidget | QLayout) -> None`
    - `set_footer(widget: QWidget | QLayout) -> None`
- **Dependencies:** `PySide6.QtWidgets`, `PySide6.QtCore`.

## Files to Modify
*No files need to be modified for the initial creation of the component.*

## Implementation Steps

### 1. Setup Directory Structure
- Ensure `src/frontend/components/` directory exists.

### 2. Implement `Card` Class in `src/frontend/components/card.py`
- **Inheritance:** Inherit from `QFrame`.
- **Initialization:**
    - Set `objectName("card")` for QSS targeting.
    - Create a vertical layout (`QVBoxLayout`) as the main layout.
    - Create the Header section (a `QWidget` or `QVBoxLayout` containing a `QLabel`).
    - Create Separator 1 (`QFrame` with `HLine` shape).
    - Create the Content section (a container `QWidget` to hold the provided widget/layout).
    - Create Separator 2 (`QFrame` with `HLine` shape).
    - Create the Footer section (a container `QWidget` to hold the provided widget/layout).
- **Logic for `set_content` and `set_footer`:**
    - If a `QLayout` is passed, the layout must be applied to the internal container widget.
    - If a `QWidget` is passed, add the widget to the container widget's layout.
    - Ensure existing content is cleared if the methods are called multiple times.

### 3. Apply QSS
- Apply the following style to the `QFrame` via `setStyleSheet` or `setObjectName`:
```css
/* Applied to the Card objectName */
QFrame[objectName="card"] {
    background-color: white;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
}

/* Styles for internal elements if needed via objectName */
QFrame[objectName="separator"] {
    background-color: #e0e0e0;
    max-height: 1px;
}
```

### 4. Implement API Methods
- `set_title(text: str) -> None`: Updates the header `QLabel`.
- `set_content(widget: QWidget | QLayout) -> None`: Manages the center section.
- `set_footer(widget: QWidget | QLayout) -> None`: Manages the bottom section.

## Proposed Class Structure
```python
from __future__ import annotations
from typing import Any
from PySide6.QtWidgets import (
    QFrame, 
    QVBoxLayout, 
    QLabel, 
    QWidget, 
    QLayout
)

class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None: ...
    def set_title(self, text: str) -> None: ...
    def set_content(self, widget: QWidget | QLayout) -> None: ...
    def set_footer(widget: QWidget | QLayout) -> None: ...
```

## Risks and Considerations
- **Layout Nesting:** Passing a `QLayout` to `set_content` requires careful management of the internal container widget.
- **Layout Margins:** The `Card` needs appropriate margins so the border doesn't touch the content directly.
- **Ownership:** Ensure `QWidget` added via `set_content` becomes a child of the container to prevent memory leaks.
