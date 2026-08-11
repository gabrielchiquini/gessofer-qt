"""Pytest configuration and fixture glue code for Gessofer-Qt.

This module re-exports fixtures from the fixtures package so that
existing tests continue to work without changes.  The actual
fixture implementations live in:

- tests/fixtures/database.py   (temp_engine, session_factory)
- tests/fixtures/orders.py     (seeded_fetch_handler, fetch_handler, sample_page)
- tests/fixtures/expenses.py   (expense_test_env, expense_list_widget)
"""
from __future__ import annotations

# Database fixtures
from tests.fixtures.database import session_factory, temp_engine

# Order fixtures
from tests.fixtures.orders import fetch_handler, sample_page, seeded_fetch_handler

# Expense fixtures
from tests.fixtures.expenses import expense_list_widget, expense_test_env

__all__ = [
    # Database
    "temp_engine",
    "session_factory",
    # Orders
    "seeded_fetch_handler",
    "fetch_handler",
    "sample_page",
    # Expenses
    "expense_test_env",
    "expense_list_widget",
]
