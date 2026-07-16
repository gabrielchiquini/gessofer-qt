from __future__ import annotations

from typing_extensions import TypedDict


class ExpenseDict(TypedDict):
    """An expense entity dict (from expense_to_dict)."""

    id: int
    month: str
    description: str
    value: int


class ExpenseInputDict(TypedDict, total=False):
    """Expense dict accepted by save_expenses bridge function.

    Only 'description' and 'value' are required.
    """

    description: str
    value: int
