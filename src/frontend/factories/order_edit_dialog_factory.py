from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtWidgets import QWidget

from backend.services.order_service import OrderService
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from models.order import Order


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class OrderEditDialogFactory(Protocol):
    """Factory protocol for creating OrderEditDialog instances."""

    def __call__(
        self,
        parent: QWidget | None,
        order_id: str | None,
        order: Order | None,
    ) -> OrderEditDialog: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _OrderEditDialogFactoryImpl:
    """Implementation of OrderEditDialogFactory backed by DI-resolved dependencies."""

    def __init__(
        self,
        order_service: OrderService,
    ) -> None:
        self._order_service: OrderService = order_service

    def __call__(
        self,
        parent: QWidget | None,
        order_id: str | None,
        order: Order | None,
    ) -> OrderEditDialog:
        return OrderEditDialog(
            parent=parent,
            order_id=order_id,
            order=order,
            order_service=self._order_service,
        )


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helper
# ──────────────────────────────────────────────────────────────────────


def _make_order_edit_dialog_factory(injector: Any) -> OrderEditDialogFactory:
    """Create a closure-based OrderEditDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    order_service = inv.get(OrderService)
    return _OrderEditDialogFactoryImpl(
        order_service=order_service,
    )
