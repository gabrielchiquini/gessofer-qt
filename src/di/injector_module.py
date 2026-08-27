from __future__ import annotations

from typing import Callable, TypeVar

from injector import Injector, Module, provider, singleton
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.certificate.handler import CertificateHandler
from backend.database.connection import get_engine
from backend.sefaz.nfe_service import NfeSearchService
from backend.services.backup_service import BackupService
from backend.services.expense_service import ExpenseService
from backend.services.save_expense_service import SaveExpenseService
from backend.services.order_service import OrderService
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportService

from bridge.order import OrderBridge
from bridge.order_summary import OrderSummaryBridge
from bridge.product import ProductBridge
from frontend.factories.certificate_change_dialog_factory import CertificateChangeDialogFactory
from frontend.factories.certificate_status_view_factory import CertificateStatusViewFactory
from frontend.factories.expense_edit_dialog_factory import ExpenseEditDialogFactory
from frontend.factories.expense_list_view_factory import ExpenseListViewFactory
from frontend.factories.nfe_search_dialog_factory import NfeSearchDialogFactory
from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory
from frontend.factories.order_edit_list_view_factory import OrderEditListViewFactory
from frontend.factories.product_list_view_factory import ProductListViewFactory


def _register_protocol_types() -> None:
    """Register factory Protocol types and BusinessService in module globals for type hint resolution."""
    import importlib
    product_list_view = importlib.import_module("frontend.factories.product_list_view_factory", __package__)
    order_edit_dialog = importlib.import_module("frontend.factories.order_edit_dialog_factory", __package__)
    nfe_search_dialog = importlib.import_module("frontend.factories.nfe_search_dialog_factory", __package__)
    expense_edit_dialog = importlib.import_module("frontend.factories.expense_edit_dialog_factory", __package__)
    certificate_change_dialog = importlib.import_module("frontend.factories.certificate_change_dialog_factory",
                                                        __package__)
    order_edit_list_view = importlib.import_module("frontend.factories.order_edit_list_view_factory", __package__)
    expense_list_view = importlib.import_module("frontend.factories.expense_list_view_factory", __package__)
    certificate_status_view = importlib.import_module("frontend.factories.certificate_status_view_factory", __package__)
    globals().update({
        "ProductListViewFactory": product_list_view.ProductListViewFactory,
        "OrderEditListViewFactory": order_edit_list_view.OrderEditListViewFactory,
        "ExpenseListViewFactory": expense_list_view.ExpenseListViewFactory,
        "CertificateStatusViewFactory": certificate_status_view.CertificateStatusViewFactory,
        "OrderEditDialogFactory": order_edit_dialog.OrderEditDialogFactory,
        "ExpenseEditDialogFactory": expense_edit_dialog.ExpenseEditDialogFactory,
        "CertificateChangeDialogFactory": certificate_change_dialog.CertificateChangeDialogFactory,
        "NfeSearchDialogFactory": nfe_search_dialog.NfeSearchDialogFactory,
    })


T = TypeVar("T")


class InjectorModule(Module):
    """
    Configures all dependency bindings for the Gessofer-Qt backend.

    - Engine: provided by the existing get_engine() function (backward compatible).
    - Session factory: a factory that creates new sessions on demand (session-per-operation).
    - OrderService / SaveExpenseService: singletons that receive the Engine via @inject.
    """

    @provider
    @singleton
    def provide_engine(self) -> Engine:
        """Provide the shared database Engine via the existing get_engine() function."""
        return get_engine()

    @provider
    @singleton
    def provide_session_factory(self, engine: Engine) -> Callable[[], Session]:
        """
        Provide a session factory function.

        Each call to the returned function creates a new Session bound to the
        shared Engine. This implements the session-per-operation pattern.

        The factory captures the Engine reference resolved at configure time
        via constructor injection, avoiding circular references.

        Args:
            engine: The shared SQLAlchemy Engine (injected by the DI container).

        Returns:
            A callable that creates and returns a new SQLAlchemy Session.
        """

        def _session_factory() -> Session:
            return Session(engine)

        return _session_factory

    @provider
    @singleton
    def provide_save_expense_service(self, engine: Engine) -> SaveExpenseService:
        """Provide a singleton SaveExpenseService with the Engine injected."""
        return SaveExpenseService(engine=engine)

    @provider
    @singleton
    def provide_nfe_search_service(self) -> NfeSearchService:
        """Provide a singleton NfeSearchService."""
        return NfeSearchService()

    @provider
    @singleton
    def provide_backup_service(self) -> "BackupService":
        """Provide a singleton BackupService with the backup directory path."""
        from backend.utils.backup import discover_backup_dir

        return BackupService(backup_dir=discover_backup_dir())

    @provider
    @singleton
    def provide_order_service(
            self,
            engine: Engine,
            session_factory: Callable[[], Session],
    ) -> OrderService:
        """Provide a singleton OrderService with Engine and session_factory injected."""
        return OrderService(engine=engine, session_factory=session_factory)

    @provider
    @singleton
    def provide_expense_service(
            self,
            save_expense_service: SaveExpenseService,
            session_factory: Callable[[], Session],
    ) -> ExpenseService:
        return ExpenseService(
            save_expense_service=save_expense_service,
            session_factory=session_factory,
        )

    @provider
    @singleton
    def provide_certificate_handler(self) -> CertificateHandler:
        return CertificateHandler()

    @provider
    @singleton
    def provide_xml_import_service(self) -> XmlImportService:
        """Provide a singleton XmlImportService."""
        return XmlImportService()

    @provider
    @singleton
    def provide_validation_service(self) -> ValidationService:
        """Provide a singleton ValidationService."""
        return ValidationService()

    @provider
    @singleton
    def provide_product_bridge(self, order_service: OrderService) -> ProductBridge:
        return ProductBridge(order_service=order_service)

    @provider
    @singleton
    def provide_order_bridge(
            self,
            order_service: OrderService,
            session_factory: Callable[[], Session],
    ) -> OrderBridge:
        return OrderBridge(order_service=order_service, session_factory=session_factory)

    @provider
    @singleton
    def provide_order_summary_bridge(
            self, product_bridge: ProductBridge
    ) -> OrderSummaryBridge:
        return OrderSummaryBridge(product_bridge=product_bridge)

    @provider
    @singleton
    def provide_product_list_view_factory(
            self,
            product_bridge: ProductBridge,
    ) -> ProductListViewFactory:
        from frontend.factories.product_list_view_factory import _ProductListViewFactoryImpl
        return _ProductListViewFactoryImpl(product_bridge=product_bridge)

    @provider
    @singleton
    def provide_order_edit_dialog_factory(
            self,
            order_bridge: OrderBridge,
    ) -> OrderEditDialogFactory:
        from frontend.factories.order_edit_dialog_factory import _OrderEditDialogFactoryImpl
        return _OrderEditDialogFactoryImpl(
            order_bridge=order_bridge,
        )

    @provider
    @singleton
    def provide_nfe_search_dialog_factory(
            self,
            nfe_search_service: NfeSearchService,
    ) -> NfeSearchDialogFactory:
        from frontend.factories.nfe_search_dialog_factory import _NfeSearchDialogFactoryImpl
        return _NfeSearchDialogFactoryImpl(nfe_search_service=nfe_search_service)

    @provider
    @singleton
    def provide_expense_edit_dialog_factory(
            self,
            expense_service: ExpenseService,
    ) -> ExpenseEditDialogFactory:
        from frontend.factories.expense_edit_dialog_factory import _ExpenseEditDialogFactoryImpl
        return _ExpenseEditDialogFactoryImpl(expense_service=expense_service)

    @provider
    @singleton
    def provide_certificate_change_dialog_factory(
            self,
            certificate_handler: CertificateHandler,
    ) -> CertificateChangeDialogFactory:
        from frontend.factories.certificate_change_dialog_factory import _CertificateChangeDialogFactoryImpl
        return _CertificateChangeDialogFactoryImpl(certificate_handler=certificate_handler)

    @provider
    @singleton
    def provide_order_edit_list_view_factory(
            self,
            order_bridge: OrderBridge,
            order_summary_bridge: OrderSummaryBridge,
            order_edit_dialog_factory: OrderEditDialogFactory,
            nfe_search_dialog_factory: NfeSearchDialogFactory,
            xml_import_service: XmlImportService,
    ) -> OrderEditListViewFactory:
        from frontend.factories.order_edit_list_view_factory import _OrderEditListViewFactoryImpl
        return _OrderEditListViewFactoryImpl(
            order_bridge=order_bridge,
            order_summary_bridge=order_summary_bridge,
            order_edit_dialog_factory=order_edit_dialog_factory,
            nfe_search_dialog_factory=nfe_search_dialog_factory,
            xml_import_service=xml_import_service,
        )

    @provider
    @singleton
    def provide_expense_list_view_factory(
            self,
            expense_service: ExpenseService,
            expense_edit_dialog_factory: ExpenseEditDialogFactory,
    ) -> ExpenseListViewFactory:
        from frontend.factories.expense_list_view_factory import _ExpenseListViewFactoryImpl
        return _ExpenseListViewFactoryImpl(
            expense_service=expense_service,
            expense_edit_dialog_factory=expense_edit_dialog_factory,
        )

    @provider
    @singleton
    def provide_certificate_status_view_factory(
            self,
            certificate_handler: CertificateHandler,
            certificate_change_dialog_factory: CertificateChangeDialogFactory,
    ) -> CertificateStatusViewFactory:
        from frontend.factories.certificate_status_view_factory import _CertificateStatusViewFactoryImpl
        return _CertificateStatusViewFactoryImpl(
            certificate_handler=certificate_handler,
            certificate_change_dialog_factory=certificate_change_dialog_factory,
        )


def get_injector() -> Injector:
    """
    Create and return the application-wide Injector.

    This is the composition root — called once in BackendManager.__init__().

    Returns:
        The Injector instance configured with InjectorModule.
    """
    return _get_app_injector()


# Module-level injector for use in API files
_app_injector: Injector | None = None


def _get_app_injector() -> Injector:
    """Get or create the application-wide injector (lazy initialization)."""
    global _app_injector
    if _app_injector is None:
        _app_injector = Injector(InjectorModule)
    return _app_injector


# Register Protocol types in globals for type hint resolution
_register_protocol_types()
