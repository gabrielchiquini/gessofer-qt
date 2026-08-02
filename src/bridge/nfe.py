from __future__ import annotations

import logging

from backend.injector_module import get_injector
from backend.sefaz.nfe_service import NfeSearchService

logger = logging.getLogger(__name__)

_nfe_handler: NfeSearchService | None = None


def _get_nfe_handler() -> NfeSearchService:
    """Lazy-initialize the NfeSearchService singleton."""
    global _nfe_handler
    if _nfe_handler is None:
        injector = get_injector()
        _nfe_handler = injector.get(NfeSearchService)
    return _nfe_handler


def search_nfe_key(nfe_key: str) -> str:
    """
    Search for an NFe via SEFAZ, save the XML to disk, and return the file path.

    This is the bridge function that exposes NFe search to the frontend layer.

    Args:
        nfe_key: The 44-digit NFe access key (spaces will be stripped).

    Returns:
        The absolute file path to the saved XML file.

    Raises:
        ValidationError: If the nfe_key is invalid (not 44 digits).
        XmlParseError: If the SEFAZ search fails or returns an unexpected response.
        Exception: For any other unexpected errors.
    """
    handler = _get_nfe_handler()
    return handler.search_and_save(nfe_key)
