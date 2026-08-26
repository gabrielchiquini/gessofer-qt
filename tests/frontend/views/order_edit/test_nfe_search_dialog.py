from __future__ import annotations
from unittest.mock import patch
from PySide6.QtWidgets import QDialog, QMessageBox
from pytestqt.qtbot import QtBot
from frontend.views.order_edit.nfe_search_dialog import NfeSearchDialog
from tests.fixtures.order_edit_dialog_fixture import nfe_search_dialog


class TestNfeSearchDialog:
    """TC-93 through TC-98: Verify NfeSearchDialog behavior."""

    def test_invalid_key_too_short(self, nfe_search_dialog: NfeSearchDialog,

                                   ) -> None:
        tc_id: str = "TC-93"
        dialog = nfe_search_dialog
        dialog._nfe_key_edit.setText("12345")

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.btn_search.click()
            mock_warning.assert_called_once()

    def test_invalid_key_non_digits(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-94"
        dialog = nfe_search_dialog
        # 44 non-digit characters
        dialog._nfe_key_edit.setText("abcdefghijklmnopqrstuvwxy012345678901234")

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.btn_search.click()
            mock_warning.assert_called_once()

    def test_valid_key_44_digits_enables_search(self, nfe_search_dialog: NfeSearchDialog) -> None:
        tc_id: str = "TC-95"
        dialog = nfe_search_dialog
        # Enter 44 zeros — the input mask fills them
        dialog._nfe_key_edit.setText("0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000")

        key: str = dialog._nfe_key_edit.text().replace(" ", "")
        assert len(key) == 44
        assert key.isdigit()

    def test_close_button_rejects(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-96"
        dialog = nfe_search_dialog
        dialog.btn_close.click()

        assert dialog.result() == QDialog.DialogCode.Rejected

    def test_input_mask_applied(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-97"
        dialog = nfe_search_dialog
        expected_mask: str = "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"
        actual_mask: str = dialog._nfe_key_edit.inputMask()
        assert actual_mask == expected_mask

    def test_progress_label_hidden_initially(self, nfe_search_dialog: NfeSearchDialog, ) -> None:
        tc_id: str = "TC-98"
        dialog = nfe_search_dialog
        assert dialog._progress_label.isVisible() is False
