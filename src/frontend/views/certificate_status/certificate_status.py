from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, )

from bridge.certificate import CertificateBridge
from models.certificate import CertificateInfo


class CertificateStatusView(QWidget):
    """Display the current certificate's status."""

    def __init__(
        self,
        parent: QWidget,
        certificate_bridge: CertificateBridge,
        certificate_change_dialog_factory: CertificateChangeDialogFactory,
    ) -> None:
        from frontend.factories import CertificateChangeDialogFactory  # noqa: F401, E402

        super().__init__(parent)
        self._certificate_bridge: CertificateBridge = certificate_bridge
        self._certificate_change_dialog_factory: CertificateChangeDialogFactory = certificate_change_dialog_factory
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
        info: CertificateInfo = self._certificate_bridge.fetch_certificate_info()

        if info.is_valid:
            self.owner_label.setText(info.owner)
            self.expiration_label.setText(f"Válido até {info.expiration_date}")
        else:
            self.owner_label.setText(info.owner)
            self.expiration_label.setText("")

    def _on_change_clicked(self) -> None:
        """Handle the 'alterar certificado' button click."""

        dialog = self._certificate_change_dialog_factory(self)
        dialog.exec()
        # After dialog closes, refresh the certificate display
        self._load_certificate()
