from __future__ import annotations

from typing import Callable, TypeVar

from injector import Injector, Module, provider, singleton
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.business import BusinessService
from backend.database.connection import get_engine
from backend.sefaz.nfe_service import NfeSearchService
from backend.services.backup_service import BackupService
from backend.services.expense_fetch_handler import ExpenseFetchHandler
from backend.services.expense_save_handler import ExpenseSaveHandler
from backend.services.fetch_handler import FetchHandler
from backend.services.freight_distribution import FreightDistributionService
from backend.services.save_handler import SaveHandler
from backend.services.save_order_service import SaveExpenseService, SaveOrderService
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportService
from bridge.certificate import CertificateBridge
from backend.certificate import CertificateHandler
from bridge.expense import ExpenseBridge
from bridge.nfe import NfeBridge
from bridge.order import OrderBridge
from bridge.order_summary import OrderSummaryBridge
from bridge.product import ProductBridge
from frontend.factories import ProductListViewFactory, OrderEditDialogFactory, NfeSearchDialogFactory, \
    ExpenseEditDialogFactory, CertificateChangeDialogFactory, OrderEditListViewFactory, ExpenseListViewFactory, \
    CertificateStatusViewFactory


def _register_protocol_types() -> None:
    """Register factory Protocol types and BusinessService in module globals for type hint resolution."""
    import importlib
    factories = importlib.import_module("frontend.factories", __package__)
    business = importlib.import_module("backend.business", __package__)
    globals().update({
        "ProductListViewFactory": factories.ProductListViewFactory,
        "OrderEditListViewFactory": factories.OrderEditListViewFactory,
        "ExpenseListViewFactory": factories.ExpenseListViewFactory,
        "CertificateStatusViewFactory": factories.CertificateStatusViewFactory,
        "OrderEditDialogFactory": factories.OrderEditDialogFactory,
        "ExpenseEditDialogFactory": factories.ExpenseEditDialogFactory,
        "CertificateChangeDialogFactory": factories.CertificateChangeDialogFactory,
        "NfeSearchDialogFactory": factories.NfeSearchDialogFactory,
        "BusinessService": business.BusinessService,
    })

T = TypeVar("T")


class InjectorModule(Module):
    """
    Configures all dependency bindings for the Gessofer-Qt backend.

    - Engine: provided by the existing get_engine() function (backward compatible).
    - Session factory: a factory that creates new sessions on demand (session-per-operation).
    - SaveOrderService / SaveExpenseService: singletons that receive the Engine via @inject.
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
    def provide_save_order_service(self, engine: Engine) -> SaveOrderService:
        """Provide a singleton SaveOrderService with the Engine injected."""
        return SaveOrderService(engine=engine)

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
    def provide_fetch_handler(self, session_factory: Callable[[], Session]) -> FetchHandler:
        return FetchHandler(session_factory=session_factory)

    @provider
    @singleton
    def provide_save_handler(
            self,
            save_order_service: SaveOrderService,
            save_expense_service: SaveExpenseService,
    ) -> SaveHandler:
        return SaveHandler(
            save_order_service=save_order_service,
            save_expense_service=save_expense_service,
        )

    @provider
    @singleton
    def provide_expense_fetch_handler(
            self, session_factory: Callable[[], Session],
    ) -> ExpenseFetchHandler:
        return ExpenseFetchHandler(session_factory=session_factory)

    @provider
    @singleton
    def provide_expense_save_handler(
            self, save_expense_service: SaveExpenseService,
    ) -> ExpenseSaveHandler:
        return ExpenseSaveHandler(save_expense_service=save_expense_service)

    @provider
    @singleton
    def provide_certificate_handler(self) -> CertificateHandler:
        return CertificateHandler()

    @provider
    @singleton
    def provide_freight_distribution_service(self) -> FreightDistributionService:
        """Provide a singleton FreightDistributionService."""
        return FreightDistributionService()

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
    def provide_business_service(
            self,
            freight_service: FreightDistributionService,
            xml_service: XmlImportService,
            validation_service: ValidationService,
    ) -> "BusinessService":
        from backend.business import BusinessService
        return BusinessService(
            freight_service=freight_service,
            xml_service=xml_service,
            validation_service=validation_service,
        )

    @provider
    @singleton
    def provide_product_bridge(self, fetch_handler: FetchHandler) -> ProductBridge:
        return ProductBridge(fetch_handler=fetch_handler)

    @provider
    @singleton
    def provide_order_bridge(
            self,
            save_handler: SaveHandler,
            session_factory: Callable[[], Session],
    ) -> OrderBridge:
        return OrderBridge(save_handler=save_handler, session_factory=session_factory)

    @provider
    @singleton
    def provide_expense_bridge(
            self,
            expense_fetch_handler: ExpenseFetchHandler,
            expense_save_handler: ExpenseSaveHandler,
    ) -> ExpenseBridge:
        return ExpenseBridge(
            expense_fetch_handler=expense_fetch_handler,
            expense_save_handler=expense_save_handler,
        )

    @provider
    @singleton
    def provide_nfe_bridge(self, nfe_search_service: NfeSearchService) -> NfeBridge:
        return NfeBridge(nfe_search_service=nfe_search_service)

    @provider
    @singleton
    def provide_certificate_bridge(
            self, certificate_handler: CertificateHandler
    ) -> CertificateBridge:
        return CertificateBridge(certificate_handler=certificate_handler)

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
        from frontend.factories import _ProductListViewFactoryImpl
        return _ProductListViewFactoryImpl(product_bridge=product_bridge)

    @provider
    @singleton
    def provide_order_edit_dialog_factory(
            self,
            order_bridge: OrderBridge,
            business_service: BusinessService,
    ) -> OrderEditDialogFactory:
        from frontend.factories import _OrderEditDialogFactoryImpl
        return _OrderEditDialogFactoryImpl(
            order_bridge=order_bridge,
            business_service=business_service,
        )

    @provider
    @singleton
    def provide_nfe_search_dialog_factory(
            self,
            nfe_bridge: NfeBridge,
    ) -> NfeSearchDialogFactory:
        from frontend.factories import _NfeSearchDialogFactoryImpl
        return _NfeSearchDialogFactoryImpl(nfe_bridge=nfe_bridge)

    @provider
    @singleton
    def provide_expense_edit_dialog_factory(
            self,
            expense_bridge: ExpenseBridge,
    ) -> ExpenseEditDialogFactory:
        from frontend.factories import _ExpenseEditDialogFactoryImpl
        return _ExpenseEditDialogFactoryImpl(expense_bridge=expense_bridge)

    @provider
    @singleton
    def provide_certificate_change_dialog_factory(
            self,
            certificate_bridge: CertificateBridge,
    ) -> CertificateChangeDialogFactory:
        from frontend.factories import _CertificateChangeDialogFactoryImpl
        return _CertificateChangeDialogFactoryImpl(certificate_bridge=certificate_bridge)

    @provider
    @singleton
    def provide_order_edit_list_view_factory(
            self,
            order_bridge: OrderBridge,
            order_summary_bridge: OrderSummaryBridge,
            business_service: BusinessService,
            nfe_bridge: NfeBridge,
            order_edit_dialog_factory: OrderEditDialogFactory,
            nfe_search_dialog_factory: NfeSearchDialogFactory,
    ) -> OrderEditListViewFactory:
        from frontend.factories import _OrderEditListViewFactoryImpl
        return _OrderEditListViewFactoryImpl(
            order_bridge=order_bridge,
            order_summary_bridge=order_summary_bridge,
            business_service=business_service,
            nfe_bridge=nfe_bridge,
            order_edit_dialog_factory=order_edit_dialog_factory,
            nfe_search_dialog_factory=nfe_search_dialog_factory,
        )

    @provider
    @singleton
    def provide_expense_list_view_factory(
            self,
            expense_bridge: ExpenseBridge,
            expense_edit_dialog_factory: ExpenseEditDialogFactory,
    ) -> ExpenseListViewFactory:
        from frontend.factories import _ExpenseListViewFactoryImpl
        return _ExpenseListViewFactoryImpl(
            expense_bridge=expense_bridge,
            expense_edit_dialog_factory=expense_edit_dialog_factory,
        )

    @provider
    @singleton
    def provide_certificate_status_view_factory(
            self,
            certificate_bridge: CertificateBridge,
            certificate_change_dialog_factory: CertificateChangeDialogFactory,
    ) -> CertificateStatusViewFactory:
        from frontend.factories import _CertificateStatusViewFactoryImpl
        return _CertificateStatusViewFactoryImpl(
            certificate_bridge=certificate_bridge,
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
