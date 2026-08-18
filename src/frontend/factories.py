from __future__ import annotations

from PySide6.QtWidgets import QWidget

from bridge.certificate import CertificateBridge
from bridge.expense import ExpenseBridge
from bridge.nfe import NfeBridge
from bridge.order import OrderBridge
from bridge.order_summary import OrderSummaryBridge
from bridge.product import ProductBridge
from frontend.business import BusinessService
from frontend.views.certificate_status.certificate_change_dialog import CertificateChangeDialog
from frontend.views.certificate_status.certificate_status import CertificateStatusView
from frontend.views.expense_edit.expense_edit_dialog import ExpenseEditDialog
from frontend.views.expense_list import ExpenseListView
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from frontend.views.order_edit.order_edit_list import OrderEditListView
from frontend.views.product_list import ProductListView


def make_product_list_view(
    parent: QWidget | None = None,
    product_bridge: ProductBridge | None = None,
) -> ProductListView:
    """Create a ProductListView with DI-injected ProductBridge."""
    return ProductListView(parent=parent, product_bridge=product_bridge)


def make_order_edit_list_view(
    parent: QWidget | None = None,
    order_bridge: OrderBridge | None = None,
    order_summary_bridge: OrderSummaryBridge | None = None,
    business_service: BusinessService | None = None,
    nfe_bridge: NfeBridge | None = None,
) -> OrderEditListView:
    """Create an OrderEditListView with DI-injected dependencies."""
    return OrderEditListView(
        parent=parent,
        order_bridge=order_bridge,
        order_summary_bridge=order_summary_bridge,
        business_service=business_service,
        nfe_bridge=nfe_bridge,
    )


def make_order_edit_dialog(
    parent: QWidget | None = None,
    order_id: str | None = None,
    order: object = None,
    order_bridge: OrderBridge | None = None,
    business_service: BusinessService | None = None,
) -> OrderEditDialog:
    """Create an OrderEditDialog with DI-injected dependencies."""
    return OrderEditDialog(
        parent=parent,
        order_id=order_id,
        order=order,
        order_bridge=order_bridge,
        business_service=business_service,
    )


def make_expense_list_view(
    parent: QWidget | None = None,
    expense_bridge: ExpenseBridge | None = None,
) -> ExpenseListView:
    """Create an ExpenseListView with DI-injected ExpenseBridge."""
    return ExpenseListView(parent=parent, expense_bridge=expense_bridge)


def make_expense_edit_dialog(
    parent: QWidget,
    month: str,
    expense_bridge: ExpenseBridge | None = None,
) -> ExpenseEditDialog:
    """Create an ExpenseEditDialog with DI-injected ExpenseBridge."""
    return ExpenseEditDialog(
        parent=parent,
        month=month,
        expense_bridge=expense_bridge,
    )


def make_certificate_status_view(
    parent: QWidget | None = None,
    certificate_bridge: CertificateBridge | None = None,
) -> CertificateStatusView:
    """Create a CertificateStatusView with DI-injected CertificateBridge."""
    return CertificateStatusView(parent=parent, certificate_bridge=certificate_bridge)


def make_certificate_change_dialog(
    parent: QWidget | None = None,
    certificate_bridge: CertificateBridge | None = None,
) -> CertificateChangeDialog:
    """Create a CertificateChangeDialog with DI-injected CertificateBridge."""
    return CertificateChangeDialog(
        parent=parent,
        certificate_bridge=certificate_bridge,
    )
