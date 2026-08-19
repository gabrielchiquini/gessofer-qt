from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from PySide6.QtWidgets import QWidget

from bridge.certificate import CertificateBridge
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
        certificate_bridge: CertificateBridge,
        certificate_change_dialog_factory: CertificateChangeDialogFactory,
    ) -> None:
        self._certificate_bridge: CertificateBridge = certificate_bridge
        self._certificate_change_dialog_factory: CertificateChangeDialogFactory = certificate_change_dialog_factory

    def __call__(self, parent: QWidget) -> CertificateStatusView:
        return CertificateStatusView(
            parent=parent,
            certificate_bridge=self._certificate_bridge,
            certificate_change_dialog_factory=self._certificate_change_dialog_factory,
        )
