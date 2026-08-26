from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtWidgets import QWidget

from backend.certificate.handler import CertificateHandler
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
    """Implementation of CertificateChangeDialogFactory backed by a DI-resolved CertificateHandler."""

    def __init__(self, certificate_handler: CertificateHandler) -> None:
        self._certificate_handler: CertificateHandler = certificate_handler

    def __call__(self, parent: QWidget) -> CertificateChangeDialog:
        return CertificateChangeDialog(
            parent=parent,
            certificate_handler=self._certificate_handler,
        )


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helper
# ──────────────────────────────────────────────────────────────────────


def _make_certificate_change_dialog_factory(injector: Any) -> CertificateChangeDialogFactory:
    """Create a closure-based CertificateChangeDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    certificate_handler = inv.get(CertificateHandler)
    return _CertificateChangeDialogFactoryImpl(certificate_handler=certificate_handler)
