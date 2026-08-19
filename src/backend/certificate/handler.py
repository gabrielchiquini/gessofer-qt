from __future__ import annotations

from backend.certificate.import_pfx import save_pem_from_pfx
from backend.certificate.read_pem import get_certificate_info
from models import CertificateInfo


class CertificateHandler:
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

        save_pem_from_pfx(pfx_path, pfx_password)
        return True
