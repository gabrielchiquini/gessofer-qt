from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QWidget,
)

from backend.certificate.handler import CertificateHandler
from frontend.components.card import Card


class CertificateChangeDialog(QDialog):
    """Modal dialog for selecting a PFX certificate file and importing it."""

    def __init__(
            self,
            parent: QWidget,
            certificate_handler: CertificateHandler,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Alterar Certificado")
        self.setMinimumSize(400, 180)

        # ── DI Handler ──────────────────────────────────────────────────
        self._certificate_handler: CertificateHandler = certificate_handler

        # ── Widgets ───────────────────────────────────────────────────
        self._pfx_path: str = ""

        self.file_label: QLabel = QLabel("Certificado:", self)
        self.file_path_label: QLabel = QLabel(self)
        self.file_path_label.setText("")
        self.file_path_label.setWordWrap(False)

        self.file_button: QPushButton = QPushButton("Selecionar...", self)

        self.password_label: QLabel = QLabel("Senha:", self)
        self.password_input: QLineEdit = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.btn_save: QPushButton = QPushButton("Salvar", self)
        self.btn_save.setEnabled(False)
        self.btn_close: QPushButton = QPushButton("Fechar", self)

        # ── Card Container ────────────────────────────────────────────
        self.card: Card = Card(self)
        self.card.set_title("Certificado")

        # Content layout
        content_layout: QHBoxLayout = QHBoxLayout()
        content_layout.addWidget(self.file_label)
        content_layout.addWidget(self.file_path_label)
        content_layout.addWidget(self.file_button)

        password_layout: QHBoxLayout = QHBoxLayout()
        password_layout.addWidget(self.password_label)
        password_layout.addWidget(self.password_input)

        form_container: QWidget = QWidget(self)
        form_vlayout: QVBoxLayout = QVBoxLayout(form_container)
        form_vlayout.setContentsMargins(6, 6, 6, 6)
        form_vlayout.setSpacing(8)
        form_vlayout.addLayout(content_layout)
        form_vlayout.addLayout(password_layout)

        self.card.set_content(form_container)

        # Footer layout
        footer_layout: QHBoxLayout = QHBoxLayout()
        footer_layout.addWidget(self.btn_save)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_close)

        self.card.set_footer(footer_layout)

        # ── Main Layout ───────────────────────────────────────────────
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.addWidget(self.card)

        # ── Signal Connections ────────────────────────────────────────
        self.file_button.clicked.connect(self._on_select_file)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_close.clicked.connect(self.reject)

        # Enable/disable save button based on input state
        self.password_input.textChanged.connect(self._update_save_button_state)

    def _on_select_file(self) -> None:
        """Open a file dialog to select a PFX/P12 certificate file."""
        file_path, _filter = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo PFX",
            "",
            "Arquivos PFX (*.pfx *.p12)",
        )
        if not file_path:
            return
        self._pfx_path = file_path
        self.file_path_label.setText(file_path)
        self._update_save_button_state()

    def _on_save(self) -> None:
        """Handle the save button click — import the certificate."""
        if not self._pfx_path or not self.password_input.text():
            return

        try:
            self._certificate_handler.save_certificate_from_pfx(
                self._pfx_path, self.password_input.text(),
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro ao alterar certificado",
                str(exc),
            )

    def _update_save_button_state(self) -> None:
        """Enable save button only when both file and password are filled."""
        self.btn_save.setEnabled(bool(self._pfx_path) and bool(self.password_input.text()))

    def get_pfx_path(self) -> str:
        """Return the selected PFX file path."""
        return self._pfx_path
