from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QWidget

from bridge.product import ProductBridge
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
    """Implementation of ProductListViewFactory backed by a DI-resolved ProductBridge."""

    def __init__(self, product_bridge: ProductBridge) -> None:
        self._product_bridge: ProductBridge = product_bridge

    def __call__(self, parent: QWidget) -> ProductListView:
        return ProductListView(parent=parent, product_bridge=self._product_bridge)
