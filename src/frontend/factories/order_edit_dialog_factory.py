from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtWidgets import QWidget

from backend.business import BusinessService
from bridge.order import OrderBridge
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from models.order import Order


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class OrderEditDialogFactory(Protocol):
    """Factory protocol for creating OrderEditDialog instances."""

    def __call__(
        self,
        parent: QWidget,
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
        order_bridge: OrderBridge,
        business_service: BusinessService,
    ) -> None:
        self._order_bridge: OrderBridge = order_bridge
        self._business_service: BusinessService = business_service  # type: ignore[assignment]

    def __call__(
        self,
        parent: QWidget,
        order_id: str | None,
        order: Order | None,
    ) -> OrderEditDialog:
        return OrderEditDialog(
            parent=parent,
            order_id=order_id,
            order=order,
            order_bridge=self._order_bridge,
            business_service=self._business_service,
        )


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helper
# ──────────────────────────────────────────────────────────────────────


def _make_order_edit_dialog_factory(injector: Any) -> OrderEditDialogFactory:
    """Create a closure-based OrderEditDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    order_bridge = inv.get(OrderBridge)
    business_service = inv.get(BusinessService)  # type: ignore[assignment]
    return _OrderEditDialogFactoryImpl(
        order_bridge=order_bridge,
        business_service=business_service,
    )
