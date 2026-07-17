from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
    QLayout,
)


class Card(QFrame):
    """A reusable card container with header, content, and footer sections."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")

        # ── Header ──────────────────────────────────────────────────────
        self._header_label: QLabel = QLabel("")
        self._header_label.setStyleSheet("font-weight: bold;")

        header_container: QWidget = QWidget(self)
        header_layout: QVBoxLayout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.addWidget(self._header_label)

        # ── Separator 1 ─────────────────────────────────────────────────
        self._separator_1: QFrame = QFrame(self)
        self._separator_1.setObjectName("separator")
        self._separator_1.setFrameShape(QFrame.Shape.HLine)
        self._separator_1.setFrameShadow(QFrame.Shadow.Sunken)
        self._separator_1.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")

        # ── Content Container ───────────────────────────────────────────
        self._content_container: QWidget = QWidget(self)
        self._content_layout: QVBoxLayout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(0)

        # ── Separator 2 ─────────────────────────────────────────────────
        self._separator_2: QFrame = QFrame(self)
        self._separator_2.setObjectName("separator")
        self._separator_2.setFrameShape(QFrame.Shape.HLine)
        self._separator_2.setFrameShadow(QFrame.Shadow.Sunken)
        self._separator_2.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")

        # ── Footer Container ────────────────────────────────────────────
        self._footer_container: QWidget = QWidget(self)
        self._footer_layout: QVBoxLayout = QVBoxLayout(self._footer_container)
        self._footer_layout.setContentsMargins(12, 12, 12, 12)
        self._footer_layout.setSpacing(0)

        # ── Main Layout ─────────────────────────────────────────────────
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header_container)
        main_layout.addWidget(self._separator_1)
        main_layout.addWidget(self._content_container)
        main_layout.addWidget(self._separator_2)
        main_layout.addWidget(self._footer_container)

        # ── QSS Styles ──────────────────────────────────────────────────
        self.setStyleSheet(
            'QFrame[objectName="card"] {'
            '    background-color: white;'
            '    border: 1px solid #d0d0d0;'
            '    border-radius: 6px;'
            '}'
            'QFrame[objectName="separator"] {'
            '    background-color: #e0e0e0;'
            '    max-height: 1px;'
            '}'
        )

    def set_title(self, text: str) -> None:
        """Update the header QLabel text."""
        self._header_label.setText(text)

    def set_content(self, widget: QWidget | QLayout) -> None:
        """Set the content section with a widget or layout.

        Clears any existing content before adding new content.
        If a QWidget is passed, it becomes a child of the container
        to prevent memory leaks.
        """
        self._clear_layout(self._content_layout)

        if isinstance(widget, QLayout):
            self._content_container.setLayout(widget)
        else:
            widget.setParent(self._content_container)
            self._content_layout.addWidget(widget)

    def set_footer(self, widget: QWidget | QLayout) -> None:
        """Set the footer section with a widget or layout.

        Clears any existing footer before adding new content.
        If a QWidget is passed, it becomes a child of the container
        to prevent memory leaks.
        """
        self._clear_layout(self._footer_layout)

        if isinstance(widget, QLayout):
            self._footer_container.setLayout(widget)
        else:
            widget.setParent(self._footer_container)
            self._footer_layout.addWidget(widget)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        """Remove all widgets from a layout without deleting them."""
        while layout.count():
            item = layout.takeAt(0)
            if item is not None:
                child_widget = item.widget()
                if child_widget is not None:
                    child_widget.setParent(None)
