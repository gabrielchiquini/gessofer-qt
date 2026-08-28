from __future__ import annotations

from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Signal


class MonthFilter(QWidget):
    month_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._label = QLabel("Mês", self)

        self.month_input = QLineEdit(self)
        self.month_input.setInputMask("99/9999")
        self.month_input.setPlaceholderText("MM/AAAA")
        self.month_input.setFixedWidth(100)

        self.search_button = QPushButton("Consultar", self)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(5)

        self._layout.addWidget(self._label)
        self._layout.addWidget(self.month_input)
        self._layout.addWidget(self.search_button)
        self._layout.addStretch()

        self.search_button.clicked.connect(self._on_search)
        self.month_input.returnPressed.connect(self._on_search)

    def _on_search(self) -> None:
        self.month_selected.emit(self.month_input.text().strip())

    def set_month(self, month: str) -> None:
        self.month_input.setText(month)

    def get_month(self) -> str:
        month_text = self.month_input.text().strip()
        if len(month_text) != 7:
            return ""
        return month_text

    def clear(self) -> None:
        self.month_input.clear()
