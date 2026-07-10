from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, Slot
from PySide6.QtQml import qmlRegisterType

from backend.injector_module import get_injector
from backend.repositories.order_repository import OrderRepository
from backend.utils.currency import cents_to_display
from backend.utils.date import iso_to_br_date, parse_month_for_orders
from sqlalchemy.orm import Session
from typing import Callable


class OrderListModel(QAbstractListModel):
    """QML-accessible model for a list of orders."""

    role_names: dict[int, str] = {
        Qt.UserRole + 1: "id",
        Qt.UserRole + 2: "date",
        Qt.UserRole + 3: "supplier",
        Qt.UserRole + 4: "nfeKey",
        Qt.UserRole + 5: "freight",
        Qt.UserRole + 6: "unloading",
        Qt.UserRole + 7: "products",
    }

    data_changed = Signal()

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self._orders: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = ...) -> int:
        del parent  # unused
        return len(self._orders)

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if not index.isValid():
            return None
        order = self._orders[index.row()]
        role_name = self.role_names.get(role)
        if role_name:
            return order.get(role_name)
        return None

    def role_names(self) -> dict[int, str]:
        return self.__class__.role_names

    @Slot(str)
    def load_for_month(self, month: str) -> None:
        """Load orders for a given month and update the model."""
        injector = get_injector()
        session_factory = injector.get(Callable[[], Session])
        m, y = parse_month_for_orders(month)
        with session_factory() as session:
            raw_orders = OrderRepository(session).fetch_orders_for_month(month=m, year=y)
        self._orders = []
        for order in raw_orders:
            self._orders.append({
                "id": order.ID,
                "date": iso_to_br_date(order.DATE.isoformat()) if order.DATE else "",
                "supplier": order.SUPPLIER,
                "nfeKey": order.NFE_KEY or "",
                "freight": cents_to_display(order.FREIGHT),
                "unloading": cents_to_display(order.UNLOADING),
                "products": [
                    {
                        "id": p.ID,
                        "name": p.NAME,
                        "quantity": p.QUANTITY,
                        "price": cents_to_display(p.PRICE),
                        "total": cents_to_display(p.TOTAL_PRICE),
                        "order_id": p.ORDER_ID,
                        "itemOrdinal": p.ITEM_ORDINAL,
                    }
                    for p in order.products
                ],
            })
        self.reset()


class ExpenseListModel(QAbstractListModel):
    """QML-accessible model for a list of expenses."""

    role_names: dict[int, str] = {
        Qt.UserRole + 1: "id",
        Qt.UserRole + 2: "month",
        Qt.UserRole + 3: "description",
        Qt.UserRole + 4: "value",
    }

    data_changed = Signal()

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self._expenses: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = ...) -> int:
        del parent
        return len(self._expenses)

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if not index.isValid():
            return None
        expense = self._expenses[index.row()]
        role_name = self.role_names.get(role)
        if role_name:
            return expense.get(role_name)
        return None

    def role_names(self) -> dict[int, str]:
        return self.__class__.role_names

    @Slot(str)
    def load_for_month(self, month: str) -> None:
        """Load expenses for a given month and update the model."""
        from backend.injector_module import get_injector
        from backend.repositories.expense_repository import ExpenseRepository
        from backend.utils.date import parse_month_for_expenses

        injector = get_injector()
        session_factory = injector.get(Callable[[], Session])
        validated = parse_month_for_expenses(month)
        with session_factory() as session:
            raw_expenses = ExpenseRepository(session).fetch_expenses_for_month(month=validated)
        self._expenses = []
        for expense in raw_expenses:
            self._expenses.append({
                "id": expense.ID,
                "month": expense.MONTH,
                "description": expense.DESCRIPTION,
                "value": cents_to_display(expense.VALUE),
            })
        self.reset()
