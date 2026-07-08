from __future__ import annotations


class BackendError(Exception):
    """
    Base exception for all backend errors.

    Attributes:
        user_message: User-facing error message (in Portuguese).
        detail_message: Detailed error message for logging/debugging.
    """

    def __init__(self, user_message: str, detail_message: str = "") -> None:
        self.user_message: str = user_message
        self.detail_message: str = detail_message
        if detail_message:
            super().__init__(f"{user_message} ({detail_message})")
        else:
            super().__init__(user_message)


class ValidationError(BackendError):
    """Raised when input data fails validation."""

    def __init__(self, errors: list[str], detail_message: str = "") -> None:
        self.errors: list[str] = errors
        user_message = "; ".join(errors) if errors else "Dados inválidos"
        super().__init__(user_message, detail_message)


class DatabaseError(BackendError):
    """Raised when a database operation fails."""

    def __init__(self, detail_message: str) -> None:
        super().__init__("Erro no banco de dados", detail_message)


class XmlParseError(BackendError):
    """Raised when XML parsing fails or produces invalid data."""

    def __init__(self, message: str) -> None:
        super().__init__("Erro ao processar XML", message)
