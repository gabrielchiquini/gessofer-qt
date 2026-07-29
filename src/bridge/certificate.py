from __future__ import annotations

import logging
from typing import Callable

from backend.certificate import get_certificate_info
from bridge.models.certificate import CertificateInfo

logger = logging.getLogger(__name__)


class _CertificateHandler:
    """Handler for certificate operations."""

    def fetch_certificate_info(self) -> CertificateInfo:
        """
        Call backend get_certificate_info() and return the result.

        The backend does all parsing in a single file read.
        The bridge simply forwards the result.

        Returns:
            CertificateInfo dataclass.
        """
        return get_certificate_info()


_handler: _CertificateHandler | None = None


def _get_handler() -> _CertificateHandler:
    """Lazy-initialize the certificate handler."""
    global _handler
    if _handler is None:
        _handler = _CertificateHandler()
    return _handler


def fetch_certificate_info() -> CertificateInfo:
    """
    Fetch certificate information from the stored PEM file.

    Returns:
        CertificateInfo dataclass. On error, returns the "no certificate" default.
    """
    try:
        handler = _get_handler()
        return handler.fetch_certificate_info()
    except Exception as exc:
        logger.error("Error fetching certificate info: %s", exc)
        logger.debug("Traceback", exc_info=True)
        return CertificateInfo(
            owner="Nenhum certificado registrado",
            expiration_date="",
            is_valid=False,
        )
