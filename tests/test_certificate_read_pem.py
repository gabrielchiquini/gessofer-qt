from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.certificate.read_pem import get_certificate_info
from bridge.models.certificate import CertificateInfo

# Ensure src/ is on sys.path so backend modules can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── Fixtures ──────────────────────────────────────────────────────

TEST_PEM_PATH: Path = Path(__file__).parent / "test_cert.pem"
TEST_EXPIRED_PEM: bytes = (
    b"-----BEGIN CERTIFICATE-----\n"
    b"MIIDazCCAlOgAwIBAgIUIsTestExpired1234567890ABCD=AAAA\n"
    b"-----END CERTIFICATE-----\n"
)


@pytest.fixture()
def valid_pem_path() -> Path:
    """Path to the valid test certificate PEM file."""
    return TEST_PEM_PATH


@pytest.fixture()
def expired_pem_content() -> bytes:
    """Raw bytes of an already-expired certificate PEM."""
    return TEST_EXPIRED_PEM


# ── Tests ─────────────────────────────────────────────────────────

def test_get_certificate_info_no_file() -> None:
    """When the PEM file does not exist, return the 'no certificate' default."""
    # Point CERTIFICATE_FILE to a non-existent path
    fake_path = Path("/nonexistent/path/certificate.pem")

    with patch.object(
            __import__("backend.certificate.read_pem", fromlist=["CERTIFICATE_FILE"]),
            "CERTIFICATE_FILE",
            fake_path,
            create=True,
    ):
        # We need to patch the module-level constant used inside the function.
        # The simplest approach: import the module and patch directly.
        import backend.certificate.read_pem as read_pem_module
        original = read_pem_module.CERTIFICATE_FILE
        read_pem_module.CERTIFICATE_FILE = fake_path
        try:
            result = get_certificate_info()
            assert result == CertificateInfo(
                owner="Nenhum certificado registrado",
                expiration_date="",
                is_valid=False,
            )
        finally:
            read_pem_module.CERTIFICATE_FILE = original


def test_get_certificate_info_valid(valid_pem_path: Path) -> None:
    """When a valid PEM file is present, return CertificateInfo with correct CN and date."""
    import backend.certificate.read_pem as read_pem_module
    original = read_pem_module.CERTIFICATE_FILE
    read_pem_module.CERTIFICATE_FILE = valid_pem_path
    try:
        result = get_certificate_info()
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
        read_pem_module.CERTIFICATE_FILE = original


def test_get_certificate_info_corrupted_file() -> None:
    """When the file contains invalid PEM data, return the 'no certificate' default."""
    import backend.certificate.read_pem as read_pem_module
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
        f.write(b"this is not a certificate")
        f.flush()
        fake_path = Path(f.name)

    try:
        original = read_pem_module.CERTIFICATE_FILE
        read_pem_module.CERTIFICATE_FILE = fake_path
        result = get_certificate_info()
        assert result.is_valid is False
        assert result.owner == "Nenhum certificado registrado"
        assert result.expiration_date == ""
    finally:
        read_pem_module.CERTIFICATE_FILE = original
        fake_path.unlink(missing_ok=True)


def test_get_certificate_info_empty_file() -> None:
    """When the file is empty, return the 'no certificate' default."""
    import backend.certificate.read_pem as read_pem_module
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="wb") as f:
        f.write(b"")
        f.flush()
        fake_path = Path(f.name)

    try:
        original = read_pem_module.CERTIFICATE_FILE
        read_pem_module.CERTIFICATE_FILE = fake_path
        result = get_certificate_info()
        assert result.is_valid is False
        assert result.owner == "Nenhum certificado registrado"
    finally:
        read_pem_module.CERTIFICATE_FILE = original
        fake_path.unlink(missing_ok=True)
