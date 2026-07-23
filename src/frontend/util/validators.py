from __future__ import annotations

from PySide6.QtGui import QValidator


class DateValidator(QValidator):
    """Validates Brazilian date format DD/MM/AAAA with semantic checks.

    The ``input_mask="99/99/9999"`` on the QLineEdit already ensures
    the text is digit-only with slashes in the right positions.
    This validator checks that the parsed values represent a plausible date:

    - Day:   1-31
    - Month: 1-12
    - Year:  >= 1900

    Returns ``Intermediate`` while the user is still typing (incomplete date).
    """

    def validate(self, input_field: str, pos: int) -> QValidator.State:
        # During typing the mask may produce partial strings like "1/" or "10/7/"
        if "/" not in input_field or len(input_field) < 8:
            return QValidator.State.Intermediate

        parts: list[str] = input_field.split("/")
        if len(parts) != 3:
            return QValidator.State.Intermediate

        try:
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            return QValidator.State.Intermediate

        if not (1 <= d <= 31 and 1 <= m <= 12 and y >= 1900):
            return QValidator.State.Intermediate

        return QValidator.State.Acceptable
