from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtWidgets import QWidget

from bridge.certificate import CertificateBridge
from frontend.views.certificate_status.certificate_change_dialog import CertificateChangeDialog


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class CertificateChangeDialogFactory(Protocol):
    """Factory protocol for creating CertificateChangeDialog instances."""

    def __call__(self, parent: QWidget) -> CertificateChangeDialog: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _CertificateChangeDialogFactoryImpl:
    """Implementation of CertificateChangeDialogFactory backed by a DI-resolved CertificateBridge."""

    def __init__(self, certificate_bridge: CertificateBridge) -> None:
        self._certificate_bridge: CertificateBridge = certificate_bridge

    def __call__(self, parent: QWidget) -> CertificateChangeDialog:
        return CertificateChangeDialog(
            parent=parent,
            certificate_bridge=self._certificate_bridge,
        )


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helper
# ──────────────────────────────────────────────────────────────────────


def _make_certificate_change_dialog_factory(injector: Any) -> CertificateChangeDialogFactory:
    """Create a closure-based CertificateChangeDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    certificate_bridge = inv.get(CertificateBridge)
    return _CertificateChangeDialogFactoryImpl(certificate_bridge=certificate_bridge)
