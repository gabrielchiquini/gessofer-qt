from __future__ import annotations

from typing import Callable

from PySide6.QtGui import (
    QFont,
    QRegularExpressionValidator,
    QValidator,
)
from PySide6.QtWidgets import QSizePolicy, QLabel, QLineEdit, QVBoxLayout, QWidget


class _RequiredValidator(QValidator):
    """QValidator that enforces a non-empty (non-whitespace) field."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def validate(self, input_field: str, pos: int) -> QValidator.State:
        if input_field.strip():
            return QValidator.State.Acceptable
        return QValidator.State.Intermediate


class _CombinedValidator(QValidator):
    """Chains multiple QValidators together.

    Returns the worst (lowest) State among all child validators.
    ``Invalid`` trumps ``Intermediate``, which trumps ``Acceptable``.
    """

    def __init__(
            self,
            parent: QWidget | None = None,
            *validators: QValidator,
    ) -> None:
        super().__init__(parent)
        self._validators: list[QValidator] = list(validators)

    def validate(self, input_field: str, pos: int) -> QValidator.State:
        worst: QValidator.State = QValidator.State.Acceptable
        for validator in self._validators:
            state = validator.validate(input_field, pos)
            if state == QValidator.State.Invalid:
                return QValidator.State.Invalid
            if state == QValidator.State.Intermediate:
                worst = QValidator.State.Intermediate
        return worst


class TextField(QWidget):
    """Reusable text input widget with label and error feedback.

    Wraps a QLineEdit inside a vertical layout with a label above and an
    optional red error-feedback label below.  Validation is performed by a
    chained QValidator that combines:

    - A required-field validator (whitespace-only is invalid)
    - An optional custom QValidator (e.g. ``QRegularExpressionValidator``)
    - An optional regex-based QRegularExpressionValidator

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
            custom_validator: QValidator | None = None,
            custom_error_message: str | None = None,
    ) -> None:
        """Initialize the TextField.

        Args:
            parent: Parent widget.
            label: Label text displayed above the edit field.
            placeholder: Placeholder text shown in the QLineEdit when empty.
            input_mask: QInputMask pattern (e.g. ``"00/00/0000"``).
            required: Whether the field is required (whitespace-only is invalid).
            regex_validation_pattern: Regex pattern string for validation.
            custom_validator: A QValidator instance to apply to the QLineEdit.
            custom_error_message: Custom error message to show on validation failure (overrides default).
        """
        super().__init__(parent)

        # ── Internal state ────────────────────────────────────────────
        self._required: bool = required
        self._error_message: str = ""
        self._was_validated: bool = False
        self._custom_error_message: str | None = custom_error_message

        # ── Internal widgets ──────────────────────────────────────────
        self._label: QLabel = QLabel(label, self)
        self._edit: QLineEdit = QLineEdit(self)
        self._error: QLabel = QLabel("", self)

        # Error label styling: 9px, red
        _error_font: QFont = QFont()
        _error_font.setPixelSize(9)
        self._error.setFont(_error_font)
        self._error.setStyleSheet("color: #bc2f32;")

        # QLineEdit setup
        self._edit.setPlaceholderText(placeholder)
        self._edit.setContentsMargins(0,0,0,0)
        if input_mask is not None:
            self._edit.setInputMask(input_mask)

        # ── Build the validator chain ─────────────────────────────────
        _children: list[QValidator] = []

        if required:
            _children.append(_RequiredValidator(self))

        if custom_validator is not None:
            _children.append(custom_validator)

        if regex_validation_pattern is not None:
            _children.append(
                QRegularExpressionValidator(regex_validation_pattern, self)
            )

        if _children:
            combined: QValidator = _CombinedValidator(self, *_children)
            self._edit.setValidator(combined)

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
        """Return whether the field is currently valid (Acceptable)."""
        return self.is_valid()

    def set_validation_state(
            self,
            error_message: str | None = None,
    ) -> None:
        """Set the validation state and optional error message.

        Args:
            error_message: Error message to display (empty if valid).
        """
        if error_message is not None:
            self._error_message = error_message
        else:
            self._error_message = ""
        self._update_validation_visibility()

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
        """Clear text, reset validation, clear error, reset was_validated."""
        self._edit.clear()
        self._error_message = ""
        self._error.setText("")
        self.set_was_validated(False)

    # ── Validate (non-mutating) ───────────────────────────────────────

    def validate(self) -> tuple[bool, str]:
        """Run validation and return ``(is_valid, error_message)`` without persisting state.

        Returns:
            A tuple of (validity, error message string).
        """
        self.set_was_validated(True)
        if self.is_valid():
            return True, ""
        return False, self._get_error_message()

    # ── Internal helpers ──────────────────────────────────────────────

    def is_valid(self) -> bool:
        """Return True if the QLineEdit validator reports Acceptable."""
        validator = self._edit.validator()
        if validator is None:
            return True
        state = validator.validate(self._edit.text(), 0)
        return state == QValidator.State.Acceptable

    def _get_error_message(self) -> str:
        """Return the error message based on validation failure type.

        Returns ``"Campo obrigatório"`` when the field is required and empty,
        ``"Valor inválido"`` for all other validation failures, or
        ``custom_error_message`` when set.
        """
        if self._custom_error_message is not None:
            return self._custom_error_message
        if self._required and not self._edit.text().strip():
            return "Campo obrigatório"
        return "Valor inválido"

    def _validate(self) -> None:
        """Run validation and persist the result to error label text."""
        if self.is_valid():
            self._error_message = ""
        else:
            self._error_message = self._get_error_message()
        self._error.setText(self._error_message)
        self._update_validation_visibility()

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

    def _update_validation_visibility(self) -> None:
        """Keep the error label always visible to occupy space.

        The error text is only shown when ``was_validated`` is True.
        """
        self._error.setText(self._error_message if self._was_validated else "")

    def _text_edited(self) -> None:
        """React to user text edits: mark as validated and re-check."""
        self.set_was_validated(True)
        self._validate()
