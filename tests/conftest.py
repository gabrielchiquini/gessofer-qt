"""Pytest configuration and fixture glue code for Gessofer-Qt.

This module re-exports fixtures from the fixtures package so that
existing tests continue to work without changes.  The actual
fixture implementations live in:

- tests/fixtures/database_fixture.py   (temp_engine, session_factory, order_service)
- tests/fixtures/orders_fixture.py     (seeded_fetch_handler, sample_page)
- tests/fixtures/expenses_fixture.py   (expense_list_widget)
- tests/fixtures/expenses_edit_fixture.py (expense_edit_dialog, expense_edit_dialog_august)
"""
from __future__ import annotations

# Database fixtures
from tests.fixtures.database_fixture import order_service, session_factory, temp_engine

# Order fixtures
from tests.fixtures.orders_fixture import sample_page, seeded_fetch_handler

# Expense fixtures
from tests.fixtures.expenses_fixture import expense_list_widget

# Product fixtures
from tests.fixtures.products_fixture import product_list_widget

# Order list fixtures
from tests.fixtures.order_list_fixture import order_list_widget

# Expense edit fixtures
from tests.fixtures.expenses_edit_fixture import expense_edit_dialog, expense_edit_dialog_august

# Order edit fixtures
from tests.fixtures.order_edit_dialog_fixture import (
    order_edit_dialog_existing,
    order_edit_dialog_blank,
    order_edit_dialog_xml_import,
    product_row_widget,
    nfe_search_dialog,
)

__all__ = [
    # Database
    "temp_engine",
    "session_factory",
    "order_service",
    # Orders
    "seeded_fetch_handler",
    "sample_page",
    # Expenses
    "expense_list_widget",
    # Order list
    "order_list_widget",
    # Products
    "product_list_widget",
    # Expense edit
    "expense_edit_dialog",
    "expense_edit_dialog_august",
    # Order edit
    "order_edit_dialog_existing",
    "order_edit_dialog_blank",
    "order_edit_dialog_xml_import",
    "product_row_widget",
    "nfe_search_dialog",
]
