from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class NfeSearchDialog(QDialog):
    """Dialog for entering an NFe access key to consult via SEFAZ."""

    nfe_searched: Signal = Signal(str)
    closed: Signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumSize(500, 200)
        self.setWindowTitle("Consultar NFe")

        # ── Label ─────────────────────────────────────────────────────
        self._label: QLabel = QLabel("Chave de acesso da NFe", self)

        # ── Input field ───────────────────────────────────────────────
        self._nfe_key_edit: QLineEdit = QLineEdit(self)
        self._nfe_key_edit.setInputMask(
            "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"
        )
        self._nfe_key_edit.setPlaceholderText(
            "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"
        )
        self._nfe_key_edit.setObjectName("nfe_key_input")
        self._nfe_key_edit.setContentsMargins(0, 0, 0, 0)

        # ── Buttons ───────────────────────────────────────────────────
        self.btn_search: QPushButton = QPushButton("Consultar", self)
        self.btn_close: QPushButton = QPushButton("Fechar", self)

        # ── Footer frame ──────────────────────────────────────────────
        footer_frame = QHBoxLayout()
        footer_frame.addWidget(self.btn_search)
        footer_frame.addStretch()
        footer_frame.addWidget(self.btn_close)

        footer_container = QWidget(self)
        footer_container.setLayout(footer_frame)

        # ── Main layout ───────────────────────────────────────────────
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self._label)
        layout.addWidget(self._nfe_key_edit)
        layout.addStretch()
        layout.addWidget(footer_container)

        # ── Signal connections ────────────────────────────────────────
        self.btn_search.clicked.connect(self._on_consultar)
        self.btn_close.clicked.connect(self._on_fechar)

    def _on_consultar(self) -> None:
        """Handle Consultar button click."""
        raw_text: str = self._nfe_key_edit.text()
        key: str = raw_text.replace(" ", "")

        if len(key) != 44 or not key.isdigit():
            QMessageBox.warning(
                self,
                "Chave inválida",
                "A chave de acesso deve conter 44 dígitos numéricos.",
            )
            return

        self.nfe_searched.emit(key)
        self.accept()

    def _on_fechar(self) -> None:
        """Handle Fechar button click."""
        self.closed.emit()
        self.reject()
