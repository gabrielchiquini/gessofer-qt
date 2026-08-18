from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from injector import Injector, Module, provider, singleton
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.sefaz.nfe_service import NfeSearchService
from backend.services.backup_service import BackupService
from backend.services.freight_distribution import FreightDistributionService
from backend.services.save_order_service import SaveExpenseService, SaveOrderService
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportService
from backend.services.fetch_handler import FetchHandler
from backend.services.save_handler import SaveHandler
from backend.services.expense_fetch_handler import ExpenseFetchHandler
from backend.services.expense_save_handler import ExpenseSaveHandler
from bridge.certificate import _CertificateHandler
from bridge.product import ProductBridge
from bridge.order import OrderBridge
from bridge.expense import ExpenseBridge
from bridge.nfe import NfeBridge
from bridge.certificate import CertificateBridge
from bridge.order_summary import OrderSummaryBridge

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
    def provide_certificate_handler(self) -> _CertificateHandler:
        return _CertificateHandler()

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
    ) -> object:
        from frontend.business import BusinessService
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
        self, certificate_handler: _CertificateHandler
    ) -> CertificateBridge:
        return CertificateBridge(certificate_handler=certificate_handler)

    @provider
    @singleton
    def provide_order_summary_bridge(
        self, product_bridge: ProductBridge
    ) -> OrderSummaryBridge:
        return OrderSummaryBridge(product_bridge=product_bridge)


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
