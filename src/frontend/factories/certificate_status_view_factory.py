from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from PySide6.QtWidgets import QWidget

from backend.certificate.handler import CertificateHandler
from frontend.views.certificate_status.certificate_status import CertificateStatusView
from frontend.factories.certificate_change_dialog_factory import CertificateChangeDialogFactory


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class CertificateStatusViewFactory(Protocol):
    """Factory protocol for creating CertificateStatusView instances."""

    def __call__(self, parent: QWidget) -> CertificateStatusView: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _CertificateStatusViewFactoryImpl:
    """Implementation of CertificateStatusViewFactory backed by DI-resolved dependencies."""

    def __init__(
        self,
        certificate_handler: CertificateHandler,
        certificate_change_dialog_factory: CertificateChangeDialogFactory,
    ) -> None:
        self._certificate_handler: CertificateHandler = certificate_handler
        self._certificate_change_dialog_factory: CertificateChangeDialogFactory = certificate_change_dialog_factory

    def __call__(self, parent: QWidget) -> CertificateStatusView:
        return CertificateStatusView(
            parent=parent,
            certificate_handler=self._certificate_handler,
            certificate_change_dialog_factory=self._certificate_change_dialog_factory,
        )
