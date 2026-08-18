from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from bridge.certificate import fetch_certificate_info
from models.certificate import CertificateInfo


# Ensure src/ is on sys.path so bridge modules can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ── Fixtures ──────────────────────────────────────────────────────

TEST_PEM_PATH: Path = Path(__file__).parent / "test_cert.pem"


# ── Tests ─────────────────────────────────────────────────────────

def test_fetch_certificate_info_no_file() -> None:
    """When the PEM file does not exist, fetch_certificate_info returns the 'no certificate' default."""
    import backend.certificate.read_pem as read_pem_module
    original = read_pem_module.CERTIFICATE_FILE
    read_pem_module.CERTIFICATE_FILE = Path("/nonexistent/path/certificate.pem")
    try:
        # Reset the injector so the bridge is re-created with fresh state
        import injector_module
        original_injector = injector_module._app_injector
        injector_module._app_injector = None
        try:
            result = fetch_certificate_info()
            assert result == CertificateInfo(
                owner="Nenhum certificado registrado",
                expiration_date="",
                is_valid=False,
            )
        finally:
            injector_module._app_injector = original_injector
    finally:
        read_pem_module.CERTIFICATE_FILE = original


def test_fetch_certificate_info_valid() -> None:
    """When a valid PEM file is present, fetch_certificate_info returns correct data."""
    import backend.certificate.read_pem as read_pem_module
    original = read_pem_module.CERTIFICATE_FILE
    read_pem_module.CERTIFICATE_FILE = TEST_PEM_PATH
    try:
        # Reset the injector so the bridge is re-created with fresh state
        import injector_module
        original_injector = injector_module._app_injector
        injector_module._app_injector = None
        try:
            result = fetch_certificate_info()
            assert result.is_valid is True
            assert result.owner == "Teste Certificado Gessofer"
            assert result.expiration_date != ""
            # Verify date format is dd/MM/yyyy
            parts = result.expiration_date.split("/")
            assert len(parts) == 3
            assert len(parts[0]) == 2  # day
            assert len(parts[1]) == 2  # month
            assert len(parts[2]) == 4  # year
        finally:
            injector_module._app_injector = original_injector
    finally:
        read_pem_module.CERTIFICATE_FILE = original


def test_fetch_certificate_info_expired() -> None:
    """When the certificate has expired, is_valid is False."""
    import backend.certificate.read_pem as read_pem_module
    import tempfile

    # Create an expired certificate PEM using the cryptography library
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import Encoding
    from datetime import timedelta

    # Generate a key pair
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Create a certificate that expired 1 day ago
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Expired Cert")])
    now_dt = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now_dt - timedelta(days=365))
        .not_valid_after(now_dt - timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )

    pem_data = cert.public_bytes(Encoding.PEM)

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="wb") as f:
        f.write(pem_data)
        f.flush()
        fake_path = Path(f.name)

    try:
        original = read_pem_module.CERTIFICATE_FILE
        read_pem_module.CERTIFICATE_FILE = fake_path
        # Reset the injector so the bridge is re-created with fresh state
        import injector_module
        original_injector = injector_module._app_injector
        injector_module._app_injector = None
        try:
            result = fetch_certificate_info()
            assert result.is_valid is False
            assert result.owner == "Expired Cert"
            assert result.expiration_date != ""
        finally:
            injector_module._app_injector = original_injector
    finally:
        read_pem_module.CERTIFICATE_FILE = original
        fake_path.unlink(missing_ok=True)


def test_fetch_certificate_info_corrupted() -> None:
    """When the file is corrupted, fetch_certificate_info returns the 'no certificate' default."""
    import backend.certificate.read_pem as read_pem_module
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="wb") as f:
        f.write(b"not a certificate at all")
        f.flush()
        fake_path = Path(f.name)

    try:
        original = read_pem_module.CERTIFICATE_FILE
        read_pem_module.CERTIFICATE_FILE = fake_path
        # Reset the injector so the bridge is re-created with fresh state
        import injector_module
        original_injector = injector_module._app_injector
        injector_module._app_injector = None
        try:
            result = fetch_certificate_info()
            assert result.is_valid is False
            assert result.owner == "Nenhum certificado registrado"
            assert result.expiration_date == ""
        finally:
            injector_module._app_injector = original_injector
    finally:
        read_pem_module.CERTIFICATE_FILE = original
        fake_path.unlink(missing_ok=True)
