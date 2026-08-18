from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, )

from bridge.certificate import fetch_certificate_info, CertificateBridge
from models.certificate import CertificateInfo
from frontend.views.certificate_status.certificate_change_dialog import CertificateChangeDialog


class CertificateStatusView(QWidget):
    """Display the current certificate's status."""

    def __init__(self, parent: QWidget | None = None, certificate_bridge: CertificateBridge | None = None) -> None:
        super().__init__(parent)
        self._certificate_bridge: CertificateBridge | None = certificate_bridge
        self._setup_ui()
        self._load_certificate()

    def _setup_ui(self) -> None:
        """Build the widget tree."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)

        # Row 1: Owner name + "alterar certificado" button
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)

        self.owner_label = QLabel(self)
        row1_layout.addWidget(self.owner_label)

        # Spacer to push button to the right
        row1_layout.addStretch()

        self.change_button = QPushButton("Alterar certificado", self)
        # Placeholder: no action connected yet
        self.change_button.clicked.connect(self._on_change_clicked)
        row1_layout.addWidget(self.change_button)

        layout.addLayout(row1_layout)

        # Row 2: Expiration date
        self.expiration_label = QLabel(self)
        layout.addWidget(self.expiration_label)

        # Spacer at the bottom
        layout.addStretch()

    def _load_certificate(self) -> None:
        """Fetch certificate info and update the UI labels."""
        if self._certificate_bridge is not None:
            info: CertificateInfo = self._certificate_bridge.fetch_certificate_info()
        else:
            info: CertificateInfo = fetch_certificate_info()

        if info.is_valid:
            self.owner_label.setText(info.owner)
            self.expiration_label.setText(f"Válido até {info.expiration_date}")
        else:
            self.owner_label.setText(info.owner)
            self.expiration_label.setText("")

    def _on_change_clicked(self) -> None:
        """Handle the 'alterar certificado' button click."""

        dialog = CertificateChangeDialog(self)
        dialog.exec()
        # After dialog closes, refresh the certificate display
        self._load_certificate()
