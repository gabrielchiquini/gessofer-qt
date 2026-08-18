from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QWidget

from bridge.certificate import CertificateBridge
from bridge.expense import ExpenseBridge
from bridge.nfe import NfeBridge
from bridge.order import OrderBridge
from bridge.order_summary import OrderSummaryBridge
from bridge.product import ProductBridge
from frontend.nfe_search_dialog import NfeSearchDialog
from frontend.views.certificate_status.certificate_change_dialog import CertificateChangeDialog
from frontend.views.certificate_status.certificate_status import CertificateStatusView
from frontend.views.expense_edit.expense_edit_dialog import ExpenseEditDialog
from frontend.views.expense_list import ExpenseListView
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from frontend.views.order_edit.order_edit_list import OrderEditListView
from frontend.views.product_list import ProductListView
from models.order import Order


# ──────────────────────────────────────────────────────────────────────
# Named Factory Protocol Classes
# ──────────────────────────────────────────────────────────────────────


class ProductListViewFactory(Protocol):
    """Factory protocol for creating ProductListView instances."""

    def __call__(self, parent: QWidget) -> ProductListView: ...


class OrderEditListViewFactory(Protocol):
    """Factory protocol for creating OrderEditListView instances."""

    def __call__(self, parent: QWidget) -> OrderEditListView: ...


class ExpenseListViewFactory(Protocol):
    """Factory protocol for creating ExpenseListView instances."""

    def __call__(self, parent: QWidget) -> ExpenseListView: ...


class CertificateStatusViewFactory(Protocol):
    """Factory protocol for creating CertificateStatusView instances."""

    def __call__(self, parent: QWidget) -> CertificateStatusView: ...


class OrderEditDialogFactory(Protocol):
    """Factory protocol for creating OrderEditDialog instances."""

    def __call__(
        self,
        parent: QWidget,
        order_id: str | None,
        order: Order | None,
    ) -> OrderEditDialog: ...


class ExpenseEditDialogFactory(Protocol):
    """Factory protocol for creating ExpenseEditDialog instances."""

    def __call__(self, parent: QWidget, month: str) -> ExpenseEditDialog: ...


class CertificateChangeDialogFactory(Protocol):
    """Factory protocol for creating CertificateChangeDialog instances."""

    def __call__(self, parent: QWidget) -> CertificateChangeDialog: ...


class NfeSearchDialogFactory(Protocol):
    """Factory protocol for creating NfeSearchDialog instances."""

    def __call__(self, parent: QWidget) -> NfeSearchDialog: ...


# ──────────────────────────────────────────────────────────────────────
# Factory Implementation Classes
# ──────────────────────────────────────────────────────────────────────


class _ProductListViewFactoryImpl:
    """Implementation of ProductListViewFactory backed by a DI-resolved ProductBridge."""

    def __init__(self, product_bridge: ProductBridge) -> None:
        self._product_bridge: ProductBridge = product_bridge

    def __call__(self, parent: QWidget) -> ProductListView:
        return ProductListView(parent=parent, product_bridge=self._product_bridge)


class _OrderEditDialogFactoryImpl:
    """Implementation of OrderEditDialogFactory backed by DI-resolved dependencies."""

    def __init__(
        self,
        order_bridge: OrderBridge,
        business_service: "BusinessService",
    ) -> None:
        from backend.business import BusinessService  # noqa: F401

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


class _NfeSearchDialogFactoryImpl:
    """Implementation of NfeSearchDialogFactory backed by a DI-resolved NfeBridge."""

    def __init__(self, nfe_bridge: NfeBridge) -> None:
        self._nfe_bridge: NfeBridge = nfe_bridge

    def __call__(self, parent: QWidget) -> NfeSearchDialog:
        return NfeSearchDialog(parent=parent)


class _ExpenseEditDialogFactoryImpl:
    """Implementation of ExpenseEditDialogFactory backed by a DI-resolved ExpenseBridge."""

    def __init__(self, expense_bridge: ExpenseBridge) -> None:
        self._expense_bridge: ExpenseBridge = expense_bridge

    def __call__(self, parent: QWidget, month: str) -> ExpenseEditDialog:
        return ExpenseEditDialog(
            parent=parent,
            month=month,
            expense_bridge=self._expense_bridge,
        )


class _CertificateChangeDialogFactoryImpl:
    """Implementation of CertificateChangeDialogFactory backed by a DI-resolved CertificateBridge."""

    def __init__(self, certificate_bridge: CertificateBridge) -> None:
        self._certificate_bridge: CertificateBridge = certificate_bridge

    def __call__(self, parent: QWidget) -> CertificateChangeDialog:
        return CertificateChangeDialog(
            parent=parent,
            certificate_bridge=self._certificate_bridge,
        )


class _OrderEditListViewFactoryImpl:
    """Implementation of OrderEditListViewFactory backed by DI-resolved dependencies."""

    def __init__(
        self,
        order_bridge: OrderBridge,
        order_summary_bridge: OrderSummaryBridge,
        business_service: "BusinessService",
        nfe_bridge: NfeBridge,
        order_edit_dialog_factory: OrderEditDialogFactory,
        nfe_search_dialog_factory: NfeSearchDialogFactory,
    ) -> None:
        from backend.business import BusinessService  # noqa: F401

        self._order_bridge: OrderBridge = order_bridge
        self._order_summary_bridge: OrderSummaryBridge = order_summary_bridge
        self._business_service: BusinessService = business_service  # type: ignore[assignment]
        self._nfe_bridge: NfeBridge = nfe_bridge
        self._order_edit_dialog_factory: OrderEditDialogFactory = order_edit_dialog_factory
        self._nfe_search_dialog_factory: NfeSearchDialogFactory = nfe_search_dialog_factory

    def __call__(self, parent: QWidget) -> OrderEditListView:
        return OrderEditListView(
            parent=parent,
            order_bridge=self._order_bridge,
            order_summary_bridge=self._order_summary_bridge,
            business_service=self._business_service,
            nfe_bridge=self._nfe_bridge,
            order_edit_dialog_factory=self._order_edit_dialog_factory,
            nfe_search_dialog_factory=self._nfe_search_dialog_factory,
        )


class _ExpenseListViewFactoryImpl:
    """Implementation of ExpenseListViewFactory backed by DI-resolved dependencies."""

    def __init__(
        self,
        expense_bridge: ExpenseBridge,
        expense_edit_dialog_factory: ExpenseEditDialogFactory,
    ) -> None:
        self._expense_bridge: ExpenseBridge = expense_bridge
        self._expense_edit_dialog_factory: ExpenseEditDialogFactory = expense_edit_dialog_factory

    def __call__(self, parent: QWidget) -> ExpenseListView:
        return ExpenseListView(
            parent=parent,
            expense_bridge=self._expense_bridge,
            expense_edit_dialog_factory=self._expense_edit_dialog_factory,
        )


class _CertificateStatusViewFactoryImpl:
    """Implementation of CertificateStatusViewFactory backed by DI-resolved dependencies."""

    def __init__(
        self,
        certificate_bridge: CertificateBridge,
        certificate_change_dialog_factory: CertificateChangeDialogFactory,
    ) -> None:
        self._certificate_bridge: CertificateBridge = certificate_bridge
        self._certificate_change_dialog_factory: CertificateChangeDialogFactory = certificate_change_dialog_factory

    def __call__(self, parent: QWidget) -> CertificateStatusView:
        return CertificateStatusView(
            parent=parent,
            certificate_bridge=self._certificate_bridge,
            certificate_change_dialog_factory=self._certificate_change_dialog_factory,
        )


# ──────────────────────────────────────────────────────────────────────
# Inner Factory Helpers
# ──────────────────────────────────────────────────────────────────────


def _make_order_edit_dialog_factory(injector: Any) -> OrderEditDialogFactory:
    """Create a closure-based OrderEditDialogFactory from the DI container."""
    from backend.business import BusinessService

    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    order_bridge = inv.get(OrderBridge)
    business_service = inv.get(BusinessService)  # type: ignore[assignment]
    return _OrderEditDialogFactoryImpl(
        order_bridge=order_bridge,
        business_service=business_service,
    )


def _make_nfe_search_dialog_factory(injector: Any) -> NfeSearchDialogFactory:
    """Create a closure-based NfeSearchDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    nfe_bridge = inv.get(NfeBridge)
    return _NfeSearchDialogFactoryImpl(nfe_bridge=nfe_bridge)


def _make_expense_edit_dialog_factory(injector: Any) -> ExpenseEditDialogFactory:
    """Create a closure-based ExpenseEditDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    expense_bridge = inv.get(ExpenseBridge)
    return _ExpenseEditDialogFactoryImpl(expense_bridge=expense_bridge)


def _make_certificate_change_dialog_factory(injector: Any) -> CertificateChangeDialogFactory:
    """Create a closure-based CertificateChangeDialogFactory from the DI container."""
    from injector import Injector

    inv: Injector = injector  # type: ignore[assignment]
    certificate_bridge = inv.get(CertificateBridge)
    return _CertificateChangeDialogFactoryImpl(certificate_bridge=certificate_bridge)


# ──────────────────────────────────────────────────────────────────────
# Standalone Convenience Functions
# ──────────────────────────────────────────────────────────────────────


def make_product_list_view(parent: QWidget) -> ProductListView:
    """Create a ProductListView using DI-injected ProductBridge."""
    from injector_module import get_injector

    injector = get_injector()
    product_bridge = injector.get(ProductBridge)
    return ProductListView(parent=parent, product_bridge=product_bridge)


def make_order_edit_list_view(parent: QWidget) -> OrderEditListView:
    """Create an OrderEditListView using DI-injected dependencies."""
    from backend.business import BusinessService

    from injector_module import get_injector

    injector = get_injector()
    order_bridge = injector.get(OrderBridge)
    order_summary_bridge = injector.get(OrderSummaryBridge)
    business_service = injector.get(BusinessService)  # type: ignore[assignment]
    nfe_bridge = injector.get(NfeBridge)
    order_edit_dialog_factory = _make_order_edit_dialog_factory(injector)
    nfe_search_dialog_factory = _make_nfe_search_dialog_factory(injector)
    return OrderEditListView(
        parent=parent,
        order_bridge=order_bridge,
        order_summary_bridge=order_summary_bridge,
        business_service=business_service,
        nfe_bridge=nfe_bridge,
        order_edit_dialog_factory=order_edit_dialog_factory,
        nfe_search_dialog_factory=nfe_search_dialog_factory,
    )


def make_expense_list_view(parent: QWidget) -> ExpenseListView:
    """Create an ExpenseListView using DI-injected dependencies."""
    from injector_module import get_injector

    injector = get_injector()
    expense_bridge = injector.get(ExpenseBridge)
    expense_edit_dialog_factory = _make_expense_edit_dialog_factory(injector)
    return ExpenseListView(
        parent=parent,
        expense_bridge=expense_bridge,
        expense_edit_dialog_factory=expense_edit_dialog_factory,
    )


def make_certificate_status_view(parent: QWidget) -> CertificateStatusView:
    """Create a CertificateStatusView using DI-injected dependencies."""
    from injector_module import get_injector

    injector = get_injector()
    certificate_bridge = injector.get(CertificateBridge)
    certificate_change_dialog_factory = _make_certificate_change_dialog_factory(injector)
    return CertificateStatusView(
        parent=parent,
        certificate_bridge=certificate_bridge,
        certificate_change_dialog_factory=certificate_change_dialog_factory,
    )


def make_order_edit_dialog(
    parent: QWidget,
    order_id: str | None = None,
    order: Order | None = None,
) -> OrderEditDialog:
    """Create an OrderEditDialog using DI-injected dependencies."""
    from injector_module import get_injector

    injector = get_injector()
    order_edit_dialog_factory = _make_order_edit_dialog_factory(injector)
    return order_edit_dialog_factory(parent=parent, order_id=order_id, order=order)


def make_expense_edit_dialog(parent: QWidget, month: str) -> ExpenseEditDialog:
    """Create an ExpenseEditDialog using DI-injected ExpenseBridge."""
    from injector_module import get_injector

    injector = get_injector()
    expense_edit_dialog_factory = _make_expense_edit_dialog_factory(injector)
    return expense_edit_dialog_factory(parent=parent, month=month)


def make_certificate_change_dialog(parent: QWidget) -> CertificateChangeDialog:
    """Create a CertificateChangeDialog using DI-injected CertificateBridge."""
    from injector_module import get_injector

    injector = get_injector()
    certificate_change_dialog_factory = _make_certificate_change_dialog_factory(injector)
    return certificate_change_dialog_factory(parent=parent)


def make_nfe_search_dialog(parent: QWidget) -> NfeSearchDialog:
    """Create an NfeSearchDialog using DI-injected NfeBridge."""
    from injector_module import get_injector

    injector = get_injector()
    nfe_search_dialog_factory = _make_nfe_search_dialog_factory(injector)
    return nfe_search_dialog_factory(parent=parent)
