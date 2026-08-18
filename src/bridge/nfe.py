from __future__ import annotations

import logging

from backend.sefaz.nfe_service import NfeSearchService

logger = logging.getLogger(__name__)


class NfeBridge:
    """Bridge for NFe search operations."""

    def __init__(self, nfe_search_service: NfeSearchService) -> None:
        self._nfe_search_service = nfe_search_service

    def search_nfe_key(self, nfe_key: str) -> str:
        """Search for an NFe via SEFAZ, save XML, return file path."""
        return self._nfe_search_service.search_and_save(nfe_key)


# ── Backward-compatible re-exports ──────────────────────────────


def _get_nfe_bridge() -> NfeBridge:
    """Lazy-access the DI-registered NfeBridge singleton."""
    from di.injector_module import get_injector
    return get_injector().get(NfeBridge)


def search_nfe_key(nfe_key: str) -> str:
    """Backward-compatible: delegates to NfeBridge.search_nfe_key()."""
    return _get_nfe_bridge().search_nfe_key(nfe_key)
