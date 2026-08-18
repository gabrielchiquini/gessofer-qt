from __future__ import annotations

import logging

from backend.certificate import get_certificate_info
from models.certificate import CertificateInfo

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

    def save_certificate_from_pfx(self, pfx_path: str, pfx_password: str) -> bool:
        """
        Import a PFX certificate file and save the PEM certificate and private key.

        Calls the backend ``save_pem_from_pfx`` which writes the PEM files to
        ``%LOCALAPPDATA%\\gessofer-app\\certificate\\``.

        Args:
            pfx_path: Absolute path to the .pfx/.p12 file.
            pfx_password: Password for the PFX file.

        Returns:
            True on success.

        Raises:
            ValueError: If the PFX file cannot be parsed (wrong password, corrupted).
            OSError: If the output directory cannot be written.
        """
        from backend.certificate import save_pem_from_pfx

        save_pem_from_pfx(pfx_path, pfx_password)
        return True


class CertificateBridge:
    """Bridge for certificate operations."""

    def __init__(self, certificate_handler: _CertificateHandler) -> None:
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

