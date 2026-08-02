from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from injector import Injector, Module, provider, singleton
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.sefaz.nfe_service import NfeSearchService
from backend.services.save_order_service import SaveExpenseService, SaveOrderService

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

    @singleton
    def provide_save_order_service(self, engine: Engine) -> SaveOrderService:
        """Provide a singleton SaveOrderService with the Engine injected."""
        return SaveOrderService(engine=engine)

    @singleton
    def provide_save_expense_service(self, engine: Engine) -> SaveExpenseService:
        """Provide a singleton SaveExpenseService with the Engine injected."""
        return SaveExpenseService(engine=engine)

    @singleton
    def provide_nfe_search_service(self) -> NfeSearchService:
        """Provide a singleton NfeSearchService."""
        return NfeSearchService()


def get_injector() -> Injector:
    """
    Create and return the application-wide Injector.

    This is the composition root — called once in BackendManager.__init__().

    Returns:
        The Injector instance configured with InjectorModule.
    """
    return Injector(InjectorModule)


# Module-level injector for use in API files
_app_injector: Injector | None = None


def _get_app_injector() -> Injector:
    """Get or create the application-wide injector (lazy initialization)."""
    global _app_injector
    if _app_injector is None:
        _app_injector = get_injector()
    return _app_injector


def call_with_injection(callable: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Call a function with dependencies injected by the application injector.

    This is a convenience wrapper around Injector.call_with_injection() for use
    in API modules that need to create injected function wrappers.

    Args:
        callable: The function to call.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The return value of the callable.
    """
    injector = _get_app_injector()
    return injector.call_with_injection(callable, args=args, kwargs=kwargs)
