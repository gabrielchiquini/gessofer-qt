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
    - backend.injector_module._app_injector (forces re-creation of injector)
    - bridge.certificate._certificate_handler (old-style handler, if still used)
    """
    # Reset injector singleton — forces fresh injector with fresh bindings
    from di import injector_module
    injector_module._app_injector = None
