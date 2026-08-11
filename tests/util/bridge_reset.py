"""Reset helpers for bridge and injector module-level singletons.

This module encapsulates the singleton reset logic so that conftest.py
and individual test files can import a single function rather than
knowing about every private global that needs clearing.
"""
from __future__ import annotations


def reset_bridge_singletons() -> None:
    """Reset all module-level singletons used by the bridge layer.

    Must be called between tests to ensure each test starts with a clean state.
    This resets:
    - bridge.expense._fetch_handler
    - bridge.expense._save_handler
    - bridge.expense._session_factory
    - backend.injector_module._app_injector
    """
    # Reset expense bridge handlers
    import bridge.expense
    bridge.expense._fetch_handler = None
    bridge.expense._save_handler = None
    bridge.expense._session_factory = None

    # Reset injector singleton
    import backend.injector_module
    backend.injector_module._app_injector = None
