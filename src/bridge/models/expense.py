from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExpenseOutput:
    """An expense entity as returned by expense_to_dict."""
    id: int
    month: str
    description: str
    value: int


@dataclass
class ExpensesForMonthOutput:
    """Result of fetching expenses for a month, including the total."""
    expenses: list[ExpenseOutput]
    total: int


@dataclass
class ExpenseInput:
    """Expense input accepted by save_expenses bridge function."""
    description: str
    value: int
