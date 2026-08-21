from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal
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

from bridge.nfe import NfeBridge
from frontend.workers.nfe_search_worker import NfeSearchWorker

logger = logging.getLogger(__name__)


class NfeSearchDialog(QDialog):
    """Dialog for entering an NFe access key to consult via SEFAZ.

    The dialog manages a background thread for the SEFAZ call,
    showing a progress indicator while waiting.
    """

    nfe_result: Signal = Signal(str)

    def __init__(
            self,
            parent: QWidget | None,
            nfe_bridge: NfeBridge,
    ) -> None:
        super().__init__(parent)
        self._nfe_bridge: NfeBridge = nfe_bridge
        self.setModal(True)
        self.setMinimumSize(500, 220)
        self.setWindowTitle("Consultar NFe")

        self._worker: NfeSearchWorker | None = None
        self._thread: QThread | None = None
        self._is_searching: bool = False

        # ── Label ─────────────────────────────────────────────────────
        self._label: QLabel = QLabel("Chave de acesso da NFe", self)

        # ── Input field ───────────────────────────────────────────────
        self._nfe_key_edit: QLineEdit = QLineEdit(self)
        self._nfe_key_edit.setInputMask(
            "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"
        )
        self._nfe_key_edit.setPlaceholderText(
            "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"
        )
        self._nfe_key_edit.setObjectName("nfe_key_input")
        self._nfe_key_edit.setContentsMargins(0, 0, 0, 0)

        # ── Progress label (hidden by default) ────────────────────────
        self._progress_label: QLabel = QLabel("", self)
        self._progress_label.setVisible(False)

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
        layout.addWidget(self._progress_label)
        layout.addStretch()
        layout.addWidget(footer_container)

        # ── Signal connections ────────────────────────────────────────
        self.btn_search.clicked.connect(self._on_search)
        self.btn_close.clicked.connect(self._on_close)

    def _on_search(self) -> None:
        """Handle Consultar button click — start background search."""
        raw_text: str = self._nfe_key_edit.text()
        key: str = raw_text.replace(" ", "")

        if len(key) != 44 or not key.isdigit():
            QMessageBox.warning(
                self,
                "Chave inválida",
                "A chave de acesso deve conter 44 dígitos numéricos.",
            )
            return

        self._start_worker(key)

    def _start_worker(self, nfe_key: str) -> None:
        """Create and start the background worker thread."""
        self._is_searching = True
        self.btn_search.setEnabled(False)
        self._progress_label.setText("Consultando SEFAZ...")
        self._progress_label.setVisible(True)

        self._thread = QThread(self)
        self._worker = NfeSearchWorker(nfe_key, nfe_bridge=self._nfe_bridge)

        assert self._thread is not None
        assert self._worker is not None

        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start_search)
        self._worker.nfe_success.connect(self._on_nfe_success)
        self._worker.nfe_error.connect(self._on_nfe_error)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_nfe_success(self, xml_path: str) -> None:
        """Handle successful NFe search."""
        self.nfe_result.emit(xml_path)
        self._on_nfe_finished()
        self.accept()

    def _on_nfe_error(self, message: str) -> None:
        """Handle NFe search error — show message, keep dialog open."""
        self._on_nfe_finished()
        QMessageBox.critical(
            self,
            "Erro ao consultar NFe",
            f"Não foi possível consultar a NFe na SEFAZ.\n\nDetalhes: {message}",
        )

    def _on_nfe_finished(self) -> None:
        """Reset UI state after search completes (success or error)."""
        assert self._thread is not None
        assert self._worker is not None
        self._is_searching = False
        self.btn_search.setEnabled(True)
        self._progress_label.setVisible(False)
        self._thread.quit()
        self._worker.deleteLater()
        self._worker = None
        self._thread = None

    def _on_close(self) -> None:
        """Handle Fechar button click."""
        self.reject()

    def reject(self) -> None:
        """Override reject to cancel in-progress searches."""
        if self._is_searching and self._thread is not None and self._worker is not None:
            self._thread.quit()
            self._thread.wait(5000)
            self._worker.deleteLater()
        super().reject()
