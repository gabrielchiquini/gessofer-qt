from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

from backend.certificate import save_pem_from_pfx

# Ensure src/ is on sys.path so backend modules can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def _get_expected_output_dir() -> Path:
    """Return the expected certificate output directory path."""
    return Path(os.environ["LOCALAPPDATA"], "gessofer-app", "certificate")


def _get_expected_files() -> tuple[Path, Path]:
    """Return the expected certificate and key file paths."""
    output_dir = _get_expected_output_dir()
    return output_dir / "certificate.pem", output_dir / "private_key.pem"


def _clean_output_dir() -> None:
    """Remove the certificate output directory and all its contents."""
    output_dir = _get_expected_output_dir()
    if output_dir.exists():
        for child in output_dir.iterdir():
            if child.is_file():
                child.unlink()
        output_dir.rmdir()


@pytest.fixture(scope="module", autouse=True)
def clean_certificate_output() -> Any:
    """Clean the certificate output directory before and after the module tests."""
    _clean_output_dir()
    yield
    _clean_output_dir()


def test_save_pem_from_pfx_creates_files() -> None:
    """Call save_pem_from_pfx and verify both PEM files are created with valid content."""
    pfx_path: Path = Path(__file__).parent / "util" / "test.pfx"
    pfx_password: str = "test"

    test_path, key_path = save_pem_from_pfx(str(pfx_path), pfx_password)

    expected_test, expected_key = _get_expected_files()

    # Returned paths must match expected paths
    assert test_path == expected_test, f"Expected {expected_test}, got {test_path}"
    assert key_path == expected_key, f"Expected {expected_key}, got {key_path}"

    # Files must exist
    assert test_path.exists(), f"certificate file not found at {test_path}"
    assert key_path.exists(), f"Key file not found at {key_path}"

    # Read content and verify PEM structure
    test_content: str = test_path.read_text(encoding="utf-8")
    key_content: str = key_path.read_text(encoding="utf-8")

    assert test_content.startswith("-----BEGIN"), (
        f"certificate PEM does not start with '-----BEGIN', got: {test_content[:50]}"
    )
    assert test_content.endswith("-----END CERTIFICATE-----\n"), (
        f"certificate PEM does not end correctly, got: {test_content[-30:]}"
    )
    assert "CERTIFICATE" in test_content.splitlines()[0], (
        f"certificate PEM header missing 'certificate': {test_content.splitlines()[0]}"
    )

    assert key_content.startswith("-----BEGIN"), (
        f"Key PEM does not start with '-----BEGIN', got: {key_content[:50]}"
    )
    assert key_content.endswith("-----END RSA PRIVATE KEY-----\n"), (
        f"Key PEM does not end correctly, got: {key_content[-30:]}"
    )
    assert "PRIVATE KEY" in key_content.splitlines()[0], (
        f"Key PEM header missing 'PRIVATE KEY': {key_content.splitlines()[0]}"
    )


def test_save_pem_from_pfx_overwrites() -> None:
    """Call save_pem_from_pfx twice and verify the second call overwrites without error."""
    pfx_path: Path = Path(__file__).parent / "util" / "test.pfx"
    pfx_password: str = "test"

    # First call
    test_path_1, key_path_1 = save_pem_from_pfx(str(pfx_path), pfx_password)
    assert test_path_1.exists(), "First call did not create certificate file"
    assert key_path_1.exists(), "First call did not create key file"

    test_content_1: str = test_path_1.read_text(encoding="utf-8")
    key_content_1: str = key_path_1.read_text(encoding="utf-8")

    # Second call (should overwrite)
    test_path_2, key_path_2 = save_pem_from_pfx(str(pfx_path), pfx_password)

    assert test_path_2 == test_path_1, "Second call returned different certificate path"
    assert key_path_2 == key_path_1, "Second call returned different key path"

    test_content_2: str = test_path_2.read_text(encoding="utf-8")
    key_content_2: str = key_path_2.read_text(encoding="utf-8")

    assert test_content_2 == test_content_1, "certificate content changed after second call"
    assert key_content_2 == key_content_1, "Key content changed after second call"

    # Verify PEM structure still valid
    assert test_content_2.startswith("-----BEGIN"), (
        "certificate PEM invalid after overwrite"
    )
    assert key_content_2.startswith("-----BEGIN"), (
        "Key PEM invalid after overwrite"
    )


def test_save_pem_from_pfx_invalid_pfx(tmp_path: Path) -> None:
    """Pass a non-existent PFX path and verify ValueError is raised."""
    fake_pfx_path: Path = tmp_path / "nonexistent.pfx"

    with pytest.raises(ValueError, match="Failed to extract PEM from PFX file"):
        save_pem_from_pfx(str(fake_pfx_path), "test")


def test_save_pem_from_pfx_invalid_password() -> None:
    """Pass the correct PFX path but wrong password and verify ValueError is raised."""
    pfx_path: Path = Path(__file__).parent / "util" / "test.pfx"

    with pytest.raises(ValueError, match="Failed to extract PEM from PFX file"):
        save_pem_from_pfx(str(pfx_path), "wrong_password")
