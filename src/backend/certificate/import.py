"""Certificate import utilities.

Extract PEM-encoded certificates and private keys from PFX files
using the ``cryptography`` library.
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12


def extract_pem_from_pfx(pfx_path: str, pfx_password: str) -> tuple[str, str]:
    """
    Extract PEM-encoded certificate and private key from a PFX file.

    Args:
        pfx_path: Path to the .pfx/.p12 certificate file.
        pfx_password: Password for the PFX file (empty string if none).

    Returns:
        A tuple of (pem_certificate, pem_key), each as a UTF-8 string
        in PEM format that openssl would accept.

    Raises:
        ValueError: If the PFX file cannot be read or parsed (with a descriptive
            error message including the original exception).
    """
    try:
        with open(pfx_path, "rb") as f:
            pfx_data = f.read()

        password_bytes: bytes | None = pfx_password.encode() if pfx_password else None

        private_key, certificate, _additional_certs = pkcs12.load_key_and_certificates(
            pfx_data, password_bytes
        )

        pem_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        pem_cert_bytes = certificate.public_bytes(
            encoding=serialization.Encoding.PEM,
        )

        return (
            pem_cert_bytes.decode("utf-8"),
            pem_key_bytes.decode("utf-8"),
        )

    except Exception as exc:
        raise ValueError(f"Failed to extract PEM from PFX file '{pfx_path}': {exc}") from exc


def save_pem_from_pfx(pfx_path: str, pfx_password: str) -> tuple[Path, Path]:
    """
    Extract PEM-encoded certificate and private key from a PFX file and save them to disk.

    The files are saved to ``%LOCALAPPDATA%\\gessofer-app\\certificate\\``:
      - ``certificate.pem`` — the PEM-encoded X.509 certificate
      - ``private_key.pem`` — the PEM-encoded private key

    Args:
        pfx_path: Path to the .pfx/.p12 certificate file.
        pfx_password: Password for the PFX file (empty string if none).

    Returns:
        A tuple of (certificate_path, key_path), each a ``Path`` pointing to
        the saved PEM file on disk.

    Raises:
        ValueError: If the PFX file cannot be read or parsed.
        OSError: If the output directory cannot be created or files cannot be written.
    """
    pem_cert, pem_key = extract_pem_from_pfx(pfx_path, pfx_password)

    output_dir = Path(os.environ["LOCALAPPDATA"], "gessofer-app", "certificate")
    output_dir.mkdir(parents=True, exist_ok=True)

    cert_path = output_dir / "certificate.pem"
    key_path = output_dir / "private_key.pem"

    cert_path.write_text(pem_cert, encoding="utf-8")
    key_path.write_text(pem_key, encoding="utf-8")

    return cert_path, key_path

