"""Pytest configuration and fixture glue code for Gessofer-Qt.

This module re-exports fixtures from the fixtures package so that
existing tests continue to work without changes.  The actual
fixture implementations live in:

- tests/fixtures/database.py   (temp_engine, session_factory, fetch_handler)
- tests/fixtures/orders.py     (seeded_fetch_handler, sample_page)
- tests/fixtures/expenses.py   (expense_list_widget)
- tests/fixtures/expenses_edit.py (expense_edit_dialog, expense_edit_dialog_august)
"""
from __future__ import annotations

# Database fixtures
from tests.fixtures.database import fetch_handler, session_factory, temp_engine

# Order fixtures
from tests.fixtures.orders import sample_page, seeded_fetch_handler

# Expense fixtures
from tests.fixtures.expenses import expense_list_widget

# Expense edit fixtures
from tests.fixtures.expenses_edit import expense_edit_dialog, expense_edit_dialog_august

__all__ = [
    # Database
    "temp_engine",
    "session_factory",
    "fetch_handler",
    # Orders
    "seeded_fetch_handler",
    "sample_page",
    # Expenses
    "expense_list_widget",
    # Expense edit
    "expense_edit_dialog",
    "expense_edit_dialog_august",
]
