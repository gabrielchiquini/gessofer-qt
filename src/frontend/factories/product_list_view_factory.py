from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QWidget

from backend.services.order_service import OrderService
from frontend.views.product_list import ProductListView


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class ProductListViewFactory(Protocol):
    """Factory protocol for creating ProductListView instances."""

    def __call__(self, parent: QWidget) -> ProductListView: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _ProductListViewFactoryImpl:
    """Implementation of ProductListViewFactory backed by a DI-resolved OrderService."""

    def __init__(self, order_service: OrderService) -> None:
        self._order_service: OrderService = order_service

    def __call__(self, parent: QWidget) -> ProductListView:
        return ProductListView(parent=parent, order_service=self._order_service)
