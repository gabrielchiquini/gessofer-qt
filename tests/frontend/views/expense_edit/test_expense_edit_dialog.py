from __future__ import annotations

from PySide6.QtWidgets import QDialog

from tests.fixtures.expenses_edit_fixture import (
    expense_edit_dialog,
    expense_edit_dialog_august,
    expense_edit_dialog_january,
)


# ── TC-01: Dialog Initialization — July 2024 ──────────────────────


class TestExpenseEditDialogInit:
    """TC-01: Dialog loads existing July 2024 expenses into rows on open."""

    def test_dialog_initializes_with_july_expenses(
        self,
        expense_edit_dialog,
    ) -> None:
        """Open dialog for July 2024 and verify 3 seeded rows + trailing empty row."""
        # Row count: 3 seeded + 1 trailing empty = 4
        rows = expense_edit_dialog.items_card.get_expense_rows()
        assert len(rows) == 4

        # Row 0 — Material de escritório
        assert rows[0].name_input.text() == "Material de escritório"
        assert rows[0].value_input.text() == "150,00"

        # Row 1 — Taxa bancária
        assert rows[1].name_input.text() == "Taxa bancária"
        assert rows[1].value_input.text() == "75,00"

        # Row 2 — Limpeza
        assert rows[2].name_input.text() == "Limpeza"
        assert rows[2].value_input.text() == "300,00"

        # Trailing empty row
        assert rows[3].is_empty() is True

        # Total: 15000 + 7500 + 30000 = 52500 cents → "525,00"
        assert expense_edit_dialog.items_card.total_label.text() == "Total: 525,00"

    def test_dialog_initializes_with_august_expenses(
        self,
        expense_edit_dialog_august,
    ) -> None:
        """Open dialog for August 2024 and verify 2 seeded rows + trailing empty row."""
        rows = expense_edit_dialog_august.items_card.get_expense_rows()
        assert len(rows) == 3  # 2 seeded + 1 trailing

        assert rows[0].name_input.text() == "Manutenção elétrica"
        assert rows[0].value_input.text() == "450,00"
        assert rows[1].name_input.text() == "Água e esgoto"
        assert rows[1].value_input.text() == "120,00"
        assert rows[2].is_empty() is True

        # Total: 45000 + 12000 = 57000 cents → "570,00"
        assert expense_edit_dialog_august.items_card.total_label.text() == "Total: 570,00"


# ── TC-03: Save Valid Expenses ────────────────────────────────────


class TestExpenseEditDialogSave:
    """TC-03: Saving valid expenses persists via bridge and accepts dialog."""

    def test_save_valid_edited_expenses(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Edit a row, save, verify success message, signal emission, and dialog accept."""
        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[0].name_input.setText("Despesa editada")
        rows[0].value_input.setText("200,00")

        saved_month: list[str] = []
        expense_edit_dialog.expenses_saved.connect(saved_month.append)
        expense_edit_dialog.btn_save.click()
        qtbot.wait(500)

        # Success message
        assert "Salvo com sucesso!" in expense_edit_dialog.message_label.text()

        # Signal emitted with correct month
        assert len(saved_month) == 1
        assert saved_month[0] == "07/2024"

        # Dialog accepted
        assert expense_edit_dialog.result() == QDialog.DialogCode.Accepted

    def test_trailing_empty_row_excluded_from_save(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Trailing empty row is not included in the expenses list sent to bridge."""
        # Fill trailing row — triggers auto-add of new trailing row
        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[3].name_input.setText("Nova despesa")
        rows[3].value_input.setText("100,00")
        qtbot.wait(100)

        # Now there are 5 rows: 4 filled + 1 new trailing
        rows = expense_edit_dialog.items_card.get_expense_rows()
        assert len(rows) == 5

        # get_expenses_list should return 4 items (trailing excluded)
        expenses = expense_edit_dialog.items_card.get_expenses_list()
        assert len(expenses) == 4

        # Verify the new trailing row is excluded
        assert rows[4].is_empty() is True
        assert expenses[3].description == "Nova despesa"
        assert expenses[3].value == 10000  # 100,00 in cents


# ── TC-04: Save with Validation Errors ────────────────────────────


class TestExpenseEditDialogValidationErrors:
    """TC-04: Saving with validation errors does not save or accept."""

    def test_save_with_name_only_in_trailing_row(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Fill only name in trailing row — validation fails, no save, no accept."""
        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[3].name_input.setText("Nome sem valor")

        saved: list[str] = []
        expense_edit_dialog.expenses_saved.connect(saved.append)
        expense_edit_dialog.btn_save.click()
        qtbot.wait(500)

        # Row-level error visible (dialog has no error message label on validation failure)
        assert rows[3]._error.isVisible() is True
        assert "Valor obrigatório quando a descrição está preenchida" in rows[3]._error.text()

        # Signal NOT emitted
        assert len(saved) == 0

        # Dialog NOT accepted
        assert expense_edit_dialog.result() != QDialog.DialogCode.Accepted


# ── TC-05: Close Dialog ───────────────────────────────────────────


class TestExpenseEditDialogClose:
    """TC-05: Closing the dialog rejects and emits closed signal."""

    def test_close_button_rejects_and_emits_signal(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Click Fechar — dialog rejects and closed signal fires."""
        closed: list[None] = []
        expense_edit_dialog.closed.connect(lambda: closed.append(None))
        expense_edit_dialog.btn_close.click()
        qtbot.wait(100)

        assert expense_edit_dialog.result() == QDialog.DialogCode.Rejected
        assert len(closed) == 1


# ── TC-06: Auto-Add Empty Row ─────────────────────────────────────


class TestExpenseEditDialogAutoRow:
    """TC-06: Filling the trailing row triggers auto-add of a new empty row."""

    def test_auto_add_empty_row_on_trailing_fill(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Fill trailing row — a new empty row is added automatically."""
        rows = expense_edit_dialog.items_card.get_expense_rows()
        assert len(rows) == 4  # 3 seeded + 1 trailing

        # Fill trailing row
        rows[3].name_input.setText("Nova despesa")
        rows[3].value_input.setText("100,00")
        qtbot.wait(100)

        rows = expense_edit_dialog.items_card.get_expense_rows()
        assert len(rows) == 5  # new trailing row added

        # Previously filled row still has data
        assert rows[3].name_input.text() == "Nova despesa"
        assert rows[3].value_input.text() == "100,00"

        # New trailing row is empty
        assert rows[4].is_empty() is True


# ── TC-07: Delete Row ─────────────────────────────────────────────


class TestExpenseEditDialogDeleteRow:
    """TC-07: Deleting a row removes it, recalculates total, updates buttons."""

    def test_delete_row_recaldates_total_and_updates_buttons(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Delete a middle row — total recalculates, delete buttons update."""
        initial_total = expense_edit_dialog.items_card.total_label.text()
        assert initial_total == "Total: 525,00"

        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[1].delete_button.click()
        qtbot.wait(100)

        rows = expense_edit_dialog.items_card.get_expense_rows()
        assert len(rows) == 3  # 2 seeded + 1 trailing

        # Total recalculated: 15000 + 30000 = 45000 → "450,00"
        assert expense_edit_dialog.items_card.total_label.text() == "Total: 450,00"

        # Last row (trailing) delete button disabled
        assert rows[-1].delete_button.isEnabled() is False

        # First row delete button still enabled (not last)
        assert rows[0].delete_button.isEnabled() is True


# ── TC-08: Total Calculation ──────────────────────────────────────


class TestExpenseEditDialogTotal:
    """TC-08: Total label updates correctly on row changes."""

    def test_total_updates_on_value_change(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Change a row value — total recalculates correctly."""
        # Initial total
        assert expense_edit_dialog.items_card.total_label.text() == "Total: 525,00"

        # Modify row 0 value to 500,00 (50000 cents)
        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[0].value_input.setText("500,00")
        qtbot.wait(100)

        # Total: 50000 + 7500 + 30000 = 87500 → "875,00"
        assert expense_edit_dialog.items_card.total_label.text() == "Total: 875,00"

    def test_total_includes_auto_added_row(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Total includes data from a row added via auto-add."""
        # Fill trailing row to trigger auto-add
        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[3].name_input.setText("Teste")
        rows[3].value_input.setText("250,00")
        qtbot.wait(100)

        rows = expense_edit_dialog.items_card.get_expense_rows()
        assert len(rows) == 5

        # Total: 15000 + 7500 + 30000 + 25000 = 77500 → "775,00"
        assert expense_edit_dialog.items_card.total_label.text() == "Total: 775,00"


# ── TC-09: Empty Month (No Seeded Expenses) ───────────────────────


class TestExpenseEditDialogEmptyMonth:
    """TC-09: Opening a month with no expenses shows only trailing empty row."""

    def test_empty_month_shows_single_trailing_row(
        self,
        expense_edit_dialog_january,
    ) -> None:
        """Open January 2024 (no seeded expenses) — only trailing empty row, total 0,00."""
        rows = expense_edit_dialog_january.items_card.get_expense_rows()
        assert len(rows) == 1  # only trailing empty row
        assert rows[0].is_empty() is True

        assert expense_edit_dialog_january.items_card.total_label.text() == "Total: 0,00"


# ── TC-11, 12, 13, 14: Row Validation ─────────────────────────────


class TestExpenseEditDialogValidation:
    """TC-11–14: Per-row validation — name only, value only, both empty, both filled."""

    def test_name_only_validation_error(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Name filled, value empty — invalid, error message shown."""
        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[3].name_input.setText("Só nome")

        valid, errors = rows[3].validate(show_errors=True)
        assert valid is False
        assert len(errors) == 1
        assert "Valor obrigatório quando a descrição está preenchida" in errors[0]
        assert rows[3]._error.isVisible() is True

    def test_value_only_validation_error(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Value filled, name empty — invalid, error message shown."""
        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[3].value_input.setText("99,99")

        valid, errors = rows[3].validate(show_errors=True)
        assert valid is False
        assert len(errors) == 1
        assert "Descrição obrigatória quando o valor está preenchido" in errors[0]
        assert rows[3]._error.isVisible() is True

    def test_both_empty_is_valid(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Both name and value empty — valid (row will be discarded)."""
        rows = expense_edit_dialog.items_card.get_expense_rows()
        trailing = rows[-1]
        assert trailing.is_empty() is True

        valid, errors = trailing.validate(show_errors=True)
        assert valid is True
        assert len(errors) == 0
        assert trailing._error.isVisible() is False

    def test_both_filled_is_valid(
        self,
        expense_edit_dialog,
        qtbot,
    ) -> None:
        """Both name and value filled — valid, no error shown."""
        rows = expense_edit_dialog.items_card.get_expense_rows()
        rows[3].name_input.setText("Despesa válida")
        rows[3].value_input.setText("50,00")

        valid, errors = rows[3].validate(show_errors=True)
        assert valid is True
        assert len(errors) == 0
        assert rows[3]._error.isVisible() is False
