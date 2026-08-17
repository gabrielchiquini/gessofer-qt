from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CertificateInfo:
    """Certificate information as returned by the bridge layer."""
    owner: str          # CN from certificate, or "Nenhum certificado registrado"
    expiration_date: str  # "dd/MM/yyyy" formatted, or ""
    is_valid: bool        # True if cert exists and has not expired
