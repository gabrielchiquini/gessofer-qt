from __future__ import annotations

from typing_extensions import TypedDict


class ValidationDict(TypedDict):
    """Result of a validation operation as a dict."""

    valid: bool
    errors: list[str]
