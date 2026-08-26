from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QWidget

from backend.services.xml_import_service import XmlImportService
from bridge.order import OrderBridge
from bridge.order_summary import OrderSummaryBridge
from frontend.factories.nfe_search_dialog_factory import NfeSearchDialogFactory
from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory
from frontend.views.order_edit.order_edit_list import OrderEditListView


# ──────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────


class OrderEditListViewFactory(Protocol):
    """Factory protocol for creating OrderEditListView instances."""

    def __call__(self, parent: QWidget) -> OrderEditListView: ...


# ──────────────────────────────────────────────────────────────────────
# Implementation
# ──────────────────────────────────────────────────────────────────────


class _OrderEditListViewFactoryImpl:
    """Implementation of OrderEditListViewFactory backed by DI-resolved dependencies."""

    def __init__(
            self,
            order_bridge: OrderBridge,
            order_summary_bridge: OrderSummaryBridge,
            order_edit_dialog_factory: OrderEditDialogFactory,
            nfe_search_dialog_factory: NfeSearchDialogFactory,
            xml_import_service: XmlImportService,
    ) -> None:
        self._order_bridge: OrderBridge = order_bridge
        self._order_summary_bridge: OrderSummaryBridge = order_summary_bridge
        self._xml_import_service: XmlImportService = xml_import_service
        self._order_edit_dialog_factory: OrderEditDialogFactory = order_edit_dialog_factory
        self._nfe_search_dialog_factory: NfeSearchDialogFactory = nfe_search_dialog_factory

    def __call__(self, parent: QWidget) -> OrderEditListView:
        return OrderEditListView(
            parent=parent,
            order_bridge=self._order_bridge,
            order_summary_bridge=self._order_summary_bridge,
            xml_import_service=self._xml_import_service,
            order_edit_dialog_factory=self._order_edit_dialog_factory,
            nfe_search_dialog_factory=self._nfe_search_dialog_factory,
        )
