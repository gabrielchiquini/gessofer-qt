from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtWidgets import QWidget

from backend.sefaz.nfe_service import NfeSearchService
from frontend.views.order_edit.nfe_search_dialog import NfeSearchDialog


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class NfeSearchDialogFactory(Protocol):
    """Factory protocol for creating NfeSearchDialog instances."""

    def __call__(self, parent: QWidget | None) -> NfeSearchDialog: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _NfeSearchDialogFactoryImpl:
    """Implementation of NfeSearchDialogFactory backed by a DI-resolved NfeSearchService."""

    def __init__(self, nfe_search_service: NfeSearchService) -> None:
        self._nfe_search_service: NfeSearchService = nfe_search_service

    def __call__(self, parent: QWidget | None) -> NfeSearchDialog:
        return NfeSearchDialog(parent=parent, nfe_search_service=self._nfe_search_service)


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helper
# ──────────────────────────────────────────────────────────────────────


def _make_nfe_search_dialog_factory(injector: Any) -> NfeSearchDialogFactory:
    """Create a closure-based NfeSearchDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    nfe_search_service = inv.get(NfeSearchService)
    return _NfeSearchDialogFactoryImpl(nfe_search_service=nfe_search_service)
