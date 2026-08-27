from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar, QMenu, QWidget

from frontend.constants import NAV_GROUPS

SignalType = Signal(str, str)

class NavigationBar(QMenuBar):
    """A QMenuBar with dropdown menus driven by NAV_GROUPS data."""

    item_clicked = Signal(str, str)  # (label, group_title)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navbar")
        self._build_menus()
        # self.item_clicked = Signal("item_clicked", ["label", "group_title"])

    def _build_menus(self) -> None:
        """Build menus from NAV_GROUPS configuration."""
        for group in NAV_GROUPS:
            menu_title = group["title"]

            # Add the group title itself as a top-level clickable action
            direct_action = QAction(menu_title, self)
            direct_action.setObjectName(f"nav-link-{menu_title.lower()}")
            direct_action.triggered.connect(
                lambda checked=False, lbl=menu_title, grp=menu_title: self.item_clicked.emit(lbl, grp)
            )
            self.addAction(direct_action)
