from __future__ import annotations

import logging

from backend.certificate.handler import CertificateHandler
from models.certificate import CertificateInfo

logger = logging.getLogger(__name__)


class CertificateBridge:
    """Bridge for certificate operations."""

    def __init__(self, certificate_handler: CertificateHandler) -> None:
        self._certificate_handler = certificate_handler

    def fetch_certificate_info(self) -> CertificateInfo:
        """Fetch certificate information from the stored PEM file."""
        try:
            return self._certificate_handler.fetch_certificate_info()
        except Exception as exc:
            logger.error("Error fetching certificate info: %s", exc)
            logger.debug("Traceback", exc_info=True)
            return CertificateInfo(
                owner="Nenhum certificado registrado",
                expiration_date="",
                is_valid=False,
            )

    def save_certificate_from_pfx(
            self, pfx_path: str, pfx_password: str
    ) -> bool:
        """Import a PFX certificate file and save PEM + private key."""
        return self._certificate_handler.save_certificate_from_pfx(
            pfx_path, pfx_password
        )

