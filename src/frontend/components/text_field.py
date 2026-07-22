from __future__ import annotations

import re
from typing import Callable

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QSizePolicy, QLabel, QLineEdit, QVBoxLayout, QWidget


class TextField(QWidget):
    """Reusable text input widget with label and error feedback.

    Wraps a QLineEdit inside a vertical layout with a label above and an
    optional red error-feedback label below.  Supports required-field and
    regex validation.

    All UI strings are in Brazilian Portuguese.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        label: str = "",
        placeholder: str = "",
        input_mask: str | None = None,
        required: bool = False,
        regex_validation_pattern: str | None = None,
    ) -> None:
        """Initialize the TextField.

        Args:
            parent: Parent widget.
            label: Label text displayed above the edit field.
            placeholder: Placeholder text shown in the QLineEdit when empty.
            input_mask: QInputMask pattern (e.g. ``"00/00/0000"``).
            required: Whether the field is required.
            regex_validation_pattern: Regex pattern string for validation.
        """
        super().__init__(parent)

        # ── Internal state ────────────────────────────────────────────
        self._required: bool = required
        self._regex_pattern: str | None = regex_validation_pattern
        self._is_valid: bool = True
        self._error_message: str = ""
        self._was_validated: bool = False

        # ── Internal widgets ──────────────────────────────────────────
        self._label: QLabel = QLabel(label, self)
        self._edit: QLineEdit = QLineEdit(self)
        self._error: QLabel = QLabel("", self)

        # Error label styling: 9px, red
        _error_font: QFont = QFont()
        _error_font.setPixelSize(9)
        self._error.setFont(_error_font)
        self._error.setStyleSheet("color: red;")
        self._error.setVisible(False)

        # QLineEdit setup
        self._edit.setPlaceholderText(placeholder)
        if input_mask is not None:
            self._edit.setInputMask(input_mask)
        self._edit.textEdited.connect(self._text_edited)

        # ── Layout ────────────────────────────────────────────────────
        _layout: QVBoxLayout = QVBoxLayout(self)
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.setSpacing(2)
        _layout.addWidget(self._label)
        _layout.addWidget(self._edit)
        _layout.addWidget(self._error)

        # Size policy
        self._edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        # ── Initial validation ────────────────────────────────────────
        self._validate()

    # ── Property: text ────────────────────────────────────────────────

    def get_text(self) -> str:
        """Return the current text from the QLineEdit."""
        return self._edit.text()

    def set_text(self, text: str) -> None:
        """Set the text in the QLineEdit."""
        self._edit.setText(text)

    # ── Property: validation state ────────────────────────────────────

    def get_validation_state(self) -> bool:
        """Return the current validation state."""
        return self._is_valid

    def set_validation_state(
        self,
        is_valid: bool,
        error_message: str | None = None,
    ) -> None:
        """Set the validation state and optional error message.

        Args:
            is_valid: Whether the field is currently valid.
            error_message: Error message to display (empty if valid).
        """
        self._is_valid = is_valid
        if error_message is not None:
            self._error_message = error_message
        else:
            self._error_message = ""
        self._error.setText(self._error_message)

    # ── Property: was validated ───────────────────────────────────────

    def get_was_validated(self) -> bool:
        """Return whether the field has been validated."""
        return self._was_validated

    def set_was_validated(self, was_validated: bool) -> None:
        """Set the was_validated flag.

        Args:
            was_validated: Whether the field has been validated.
        """
        self._was_validated = was_validated
        self._update_validation_visibility()

    # ── Clear ─────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Clear text, reset validation to valid, clear error, reset was_validated."""
        self._edit.clear()
        self._is_valid = True
        self._error_message = ""
        self._error.setText("")
        self.set_was_validated(False)

    # ── Validate (non-mutating) ───────────────────────────────────────

    def validate(self) -> tuple[bool, str]:
        """Run validation and return ``(is_valid, error_message)`` without persisting state.

        Returns:
            A tuple of (validity, error message string).
        """
        text: str = self._edit.text()

        # Required check
        if self._required and not text.strip():
            return False, "Campo obrigatório."

        # Regex check
        if self._regex_pattern is not None and text:
            if not re.search(self._regex_pattern, text):
                return False, "Formato inválido."

        return True, ""

    # ── Internal validation ───────────────────────────────────────────

    def _validate(self) -> None:
        """Run validation and persist the result to internal state."""
        text: str = self._edit.text()

        # Required check
        if self._required and not text.strip():
            self._is_valid = False
            self._error_message = "Campo obrigatório."
            self._error.setText(self._error_message)
            return

        # Regex check
        if self._regex_pattern is not None and text:
            if not re.search(self._regex_pattern, text):
                self._is_valid = False
                self._error_message = "Formato inválido."
                self._error.setText(self._error_message)
                return

        # Both pass
        self._is_valid = True
        self._error_message = ""
        self._error.setText("")

    # ── Signal connection helpers ─────────────────────────────────────

    def connect_text_changed(self, callback: Callable[[str], None]) -> None:
        """Connect a callback to the QLineEdit ``textChanged`` signal.

        Args:
            callback: Called with the new text string on each change.
        """
        self._edit.textChanged.connect(callback)

    def connect_return_pressed(self, callback: Callable[[], None]) -> None:
        """Connect a callback to the QLineEdit ``returnPressed`` signal.

        Args:
            callback: Called when the user presses Enter/Return.
        """
        self._edit.returnPressed.connect(callback)

    def connect_text_modified(self, callback: Callable[[str], None]) -> None:
        """Connect a callback to the QLineEdit ``textModified`` signal.

        Args:
            callback: Called when the text is modified by the user.
        """
        self._edit.textEdited.connect(callback)

    def _update_validation_visibility(self):
        self._error.setVisible(self._was_validated)

    def _text_edited(self):
        self.set_was_validated(True)
        self.validate()
