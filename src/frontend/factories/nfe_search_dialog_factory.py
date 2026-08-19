from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtWidgets import QWidget

from bridge.nfe import NfeBridge
from frontend.views.order_edit.nfe_search_dialog import NfeSearchDialog


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class NfeSearchDialogFactory(Protocol):
    """Factory protocol for creating NfeSearchDialog instances."""

    def __call__(self, parent: QWidget) -> NfeSearchDialog: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _NfeSearchDialogFactoryImpl:
    """Implementation of NfeSearchDialogFactory backed by a DI-resolved NfeBridge."""

    def __init__(self, nfe_bridge: NfeBridge) -> None:
        self._nfe_bridge: NfeBridge = nfe_bridge

    def __call__(self, parent: QWidget) -> NfeSearchDialog:
        return NfeSearchDialog(parent=parent, nfe_bridge=self._nfe_bridge)


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helper
# ──────────────────────────────────────────────────────────────────────


def _make_nfe_search_dialog_factory(injector: Any) -> NfeSearchDialogFactory:
    """Create a closure-based NfeSearchDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    nfe_bridge = inv.get(NfeBridge)
    return _NfeSearchDialogFactoryImpl(nfe_bridge=nfe_bridge)
