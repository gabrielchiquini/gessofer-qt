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
            menu = self.addMenu(menu_title)
            menu.setObjectName(f"nav-menu-{menu_title.lower()}")

            for item in group["items"]:
                label = item["label"]
                group_title = item["group"]
                action = QAction(label, self)
                action.setObjectName(f"nav-link-{label.lower()}")
                action.triggered.connect(
                    lambda checked=False, lbl=label, grp=group_title: self.item_clicked.emit(lbl, grp)
                )
                menu.addAction(action)
