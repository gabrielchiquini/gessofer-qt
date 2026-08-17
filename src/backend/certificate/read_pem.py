"""Certificate reading utilities.

Reads the PEM-encoded X.509 certificate from disk and returns
a CertificateInfo dataclass in a single operation.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, UTC
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID

from models.certificate import CertificateInfo

_CERTIFICATE_DIR = Path(os.environ.get("LOCALAPPDATA", ""), "gessofer-app", "certificate")
CERTIFICATE_FILE = _CERTIFICATE_DIR / "certificate.pem"
KEY_FILE = _CERTIFICATE_DIR / "private_key.pem"

logger = logging.getLogger(__name__)

def get_certificate_info() -> CertificateInfo:
    """
    Read the PEM certificate from disk and return its information.

    Reads the file once, parses the X.509 certificate, extracts
    the Common Name (CN) from the subject, extracts the expiration
    date, formats it as 'dd/MM/yyyy', and checks validity.

    Returns:
        CertificateInfo with owner, formatted expiration, and validity flag.
        Returns the "no certificate" default if the file does not exist,
        is corrupted, or cannot be parsed.
    """
    try:
        cert_data = CERTIFICATE_FILE.read_bytes()
        cert: x509.Certificate = x509.load_pem_x509_certificate(cert_data)
    except FileNotFoundError:
        return CertificateInfo(
            owner="Nenhum certificado registrado",
            expiration_date="",
            is_valid=False,
        )
    except Exception as exc:
        logger.error(f"Error reading certificate {exc}", exc_info=True, stack_info=True)
        return CertificateInfo(
            owner="Nenhum certificado registrado",
            expiration_date="",
            is_valid=False,
        )

    # Extract CN (owner name)
    attributes = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    owner: str = attributes[0].value if attributes else ""

    # Extract expiration date
    expiration_dt: datetime = cert.not_valid_after_utc

    # Format expiration as dd/MM/yyyy
    expiration_date: str = expiration_dt.strftime("%d/%m/%Y")

    # Check validity (timezone-aware comparison)
    now: datetime = datetime.now(tz=expiration_dt.tzinfo) if expiration_dt.tzinfo is not None else datetime.now(UTC)
    is_valid: bool = expiration_dt > now

    return CertificateInfo(
        owner=owner,
        expiration_date=expiration_date,
        is_valid=is_valid,
    )

def get_certificate_pair() -> tuple[bytes, bytes]:
    certificate = CERTIFICATE_FILE.read_bytes()
    key = KEY_FILE.read_bytes()
    return certificate, key

def get_certificate_files() -> tuple[Path, Path]:
    return CERTIFICATE_FILE, KEY_FILE
