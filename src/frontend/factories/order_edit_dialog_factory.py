from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtWidgets import QWidget

from backend.services.freight_distribution import FreightDistributionService
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
        order_bridge: OrderBridge,
        freight_distribution_service: FreightDistributionService,
    ) -> None:
        self._order_bridge: OrderBridge = order_bridge
        self._freight_distribution_service: FreightDistributionService = freight_distribution_service  # type: ignore[assignment]

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
            order_bridge=self._order_bridge,
            freight_service=self._freight_distribution_service,
        )


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helper
# ──────────────────────────────────────────────────────────────────────


def _make_order_edit_dialog_factory(injector: Any) -> OrderEditDialogFactory:
    """Create a closure-based OrderEditDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    order_bridge = inv.get(OrderBridge)
    freight_service = inv.get(FreightDistributionService)  # type: ignore[assignment]
    return _OrderEditDialogFactoryImpl(
        order_bridge=order_bridge,
        freight_distribution_service=freight_service,
    )
