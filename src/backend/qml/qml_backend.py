from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, Slot
from sqlalchemy.orm import Session

from backend.injector_module import get_injector
from backend.models.dto import ExpenseInput, OrderInput
from backend.services.freight_distribution import FreightDistributionService
from backend.services.save_order_service import SaveExpenseService, SaveOrderService
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportService
from backend.qml.qml_fetch import FetchHandler
from backend.qml.qml_save import SaveHandler
from backend.qml.qml_business import BusinessHandler
from backend.qml.qml_transformers import (
    dict_to_order_input,
    expense_to_dict,
    freight_result_to_dict,
    orm_order_to_dict,
    orm_product_to_dict,
    product_page_to_dict,
    xml_import_result_to_dict,
)

logger = logging.getLogger(__name__)


class BackendManager(QObject):
    """
    QObject singleton that exposes backend API functions to QML.

    All methods are @Slot-decorated so they can be called directly from QML.
    Errors are caught and emitted via the error_occurred signal.

    This class is the composition root for the PySide6 layer — it creates
    the Injector, resolves services, and wires them together.
    """

    data_changed = Signal()
    save_completed = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # Create the injector (composition root)
        self._injector = get_injector()

        # Resolve services from the injector
        self._session_factory: Callable[[], Session] = self._injector.get(Callable[[], Session])
        self._save_order_service = self._injector.get(SaveOrderService)
        self._save_expense_service = self._injector.get(SaveExpenseService)

        # Create stateless services (no DI needed)
        self._validation = ValidationService()
        self._freight = FreightDistributionService()
        self._xml_import = XmlImportService()

        # Sub-handlers
        self._fetch_handler = FetchHandler(self._session_factory)
        self._save_handler = SaveHandler(self._save_order_service, self._save_expense_service)
        self._business_handler = BusinessHandler(self._validation, self._freight, self._xml_import)

    # ── Data Fetch ──────────────────────────────────────────────────

    @Slot(str)
    def orders_for_month(self, month: str) -> list[dict[str, Any]]:
        """Fetch orders for a month and return as list of dicts for QML."""
        try:
            raw_orders = self._fetch_handler.fetch_orders_for_month(month)
            self.data_changed.emit()
            return [orm_order_to_dict(o) for o in raw_orders]
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return []

    @Slot(int, str, str, str)
    def product_list(
        self,
        page: int,
        supplier: str = "",
        product: str = "",
        month: str = "",
    ) -> dict[str, Any]:
        """Fetch paginated product list and return as dict for QML."""
        try:
            result = self._fetch_handler.fetch_products(
                page=page,
                supplier=supplier if supplier else None,
                product=product if product else None,
                month=month if month else None,
            )
            return product_page_to_dict(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"items": [], "page": 0, "page_count": 0, "total": 0, "page_size": 0}

    @Slot(str)
    def expenses_for_month(self, month: str) -> list[dict[str, Any]]:
        """Fetch expenses for a month and return as list of dicts for QML."""
        try:
            raw_expenses = self._fetch_handler.fetch_expenses_for_month(month)
            return [expense_to_dict(e) for e in raw_expenses]
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return []

    # ── Save ────────────────────────────────────────────────────────

    @Slot(list, list)
    def save_orders(self, orders: list, deleted_orders: list) -> None:
        """Save orders in a single transaction."""
        try:
            final_orders: list[OrderInput] = [dict_to_order_input(o) for o in orders]
            self._save_handler.save_orders(final_orders, deleted_orders)
            self.save_completed.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    @Slot(list, str)
    def save_expenses(self, expenses: list, month: str) -> None:
        """Save expenses in a single transaction."""
        try:
            expense_inputs = [
                ExpenseInput(
                    description=e.get("description", ""),
                    value=e.get("value", 0),
                )
                for e in expenses
            ]
            self._save_handler.save_expenses(expense_inputs, month)
            self.save_completed.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Business Logic ──────────────────────────────────────────────

    @Slot(object)
    def distribute_freight(self, order: dict[str, Any]) -> dict[str, Any]:
        """Distribute freight costs across products in an order."""
        try:
            order_input = dict_to_order_input(order)
            result = self._business_handler.distribute_freight(order_input)
            return freight_result_to_dict(result)
        except ValueError as exc:
            self.error_occurred.emit(str(exc))
            return {}

    @Slot(str)
    def import_xml(self, file_path: str) -> dict[str, Any]:
        """Import data from an NFe XML file."""
        try:
            result = self._business_handler.import_xml(file_path)
            return xml_import_result_to_dict(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"orders": [], "warnings": []}

    @Slot(object)
    def validate_order(self, order: dict[str, Any]) -> dict[str, Any]:
        """Validate an order and return the result."""
        try:
            order_input = dict_to_order_input(order)
            result = self._business_handler.validate_order(order_input)
            return {"valid": result.valid, "errors": result.errors}
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"valid": False, "errors": [str(exc)]}

    @Slot(str, int)
    def validate_expense(self, description: str, value: int) -> dict[str, Any]:
        """Validate a single expense."""
        result = self._business_handler.validate_expense(description, value)
        return {"valid": result.valid, "errors": result.errors}
