from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.errors import ValidationError, XmlParseError
from backend.sefaz.nfe_search import _is_nfe, search_nfe

logger = logging.getLogger(__name__)


class NfeSearchService:
    """Service that searches NFe via SEFAZ, saves XML to disk, and returns the file path."""

    def search_and_save(self, nfe_key: str) -> str:
        """
        Search for an NFe via SEFAZ, save the XML to disk, and return the file path.

        Args:
            nfe_key: The 44-digit NFe access key (spaces are OK, will be stripped).

        Returns:
            The absolute file path to the saved XML file.

        Raises:
            ValidationError: If the nfe_key is invalid (not 44 digits).
            XmlParseError: If the SEFAZ search fails or returns an unexpected response.
            BackendError: For any other unexpected errors.
        """
        # 1. Validate key
        clean_key: str = nfe_key.replace(" ", "")
        if len(clean_key) != 44 or not clean_key.isdigit():
            raise ValidationError(
                ["Chave de acesso inválida. Deve conter 44 dígitos numéricos."],
                "nfe_key validation failed",
            )

        # 2. Ensure output directory exists
        output_dir: Path = Path(
            os.environ.get("LOCALAPPDATA", ""),
            "gessofer-app",
            "notas",
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # 3. Search SEFAZ
        response: str = search_nfe(clean_key)

        # 5. Save to disk
        file_path: Path = output_dir / f"{clean_key}.xml"
        file_path.write_text(response, encoding="utf-8")

        return str(file_path.resolve())
