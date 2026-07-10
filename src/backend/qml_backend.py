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

        # Resolve injected API functions
        from backend.api.orders import (
            get_orders_for_month_injected,
            get_product_list_injected,
        )
        from backend.api.save_expenses import (
            get_expenses_for_month_injected,
            get_save_expenses_injected,
        )
        from backend.api.save_orders import get_save_orders_injected

        self._orders_for_month_fn = get_orders_for_month_injected()
        self._product_list_fn = get_product_list_injected()
        self._expenses_for_month_fn = get_expenses_for_month_injected()
        self._save_orders_fn = get_save_orders_injected()
        self._save_expenses_fn = get_save_expenses_injected()

        # Create stateless services (no DI needed)
        self._validation = ValidationService()
        self._freight = FreightDistributionService()
        self._xml_import = XmlImportService()

    # ── Orders ──────────────────────────────────────────────────────

    @Slot(str)
    def orders_for_month(self, month: str) -> list[dict[str, Any]]:
        """Fetch orders for a month and return as list of dicts for QML."""
        try:
            raw_orders = self._orders_for_month_fn(month)
            result = []
            for order in raw_orders:
                result.append({
                    "id": order.ID,
                    "date": order.DATE.isoformat() if order.DATE else "",
                    "supplier": order.SUPPLIER,
                    "nfeKey": order.NFE_KEY or "",
                    "freight": order.FREIGHT,
                    "unloading": order.UNLOADING,
                    "products": [
                        {
                            "id": p.ID,
                            "name": p.NAME,
                            "quantity": p.QUANTITY,
                            "price": p.PRICE,
                            "total": p.TOTAL_PRICE,
                            "order_id": p.ORDER_ID,
                            "itemOrdinal": p.ITEM_ORDINAL,
                        }
                        for p in order.products
                    ],
                })
            self.data_changed.emit()
            return result
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
            result = self._product_list_fn(
                page=page,
                supplier=supplier if supplier else None,
                product=product if product else None,
                month=month if month else None,
            )
            return {
                "items": [
                    {
                        "id": p.ID,
                        "name": p.NAME,
                        "quantity": p.QUANTITY,
                        "price": p.PRICE,
                        "total": p.TOTAL_PRICE,
                        "order_id": p.ORDER_ID,
                        "itemOrdinal": p.ITEM_ORDINAL,
                    }
                    for p in result.items
                ],
                "page": result.page,
                "page_count": result.page_count,
                "total": result.total,
                "page_size": result.page_size,
            }
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {
                "items": [],
                "page": 0,
                "page_count": 0,
                "total": 0,
                "page_size": 0,
            }

    # ── Expenses ────────────────────────────────────────────────────

    @Slot(str)
    def expenses_for_month(self, month: str) -> list[dict[str, Any]]:
        """Fetch expenses for a month and return as list of dicts for QML."""
        try:
            raw_expenses = self._expenses_for_month_fn(month)
            return [
                {
                    "id": e.ID,
                    "month": e.MONTH,
                    "description": e.DESCRIPTION,
                    "value": e.VALUE,
                }
                for e in raw_expenses
            ]
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return []

    # ── Save Operations ─────────────────────────────────────────────

    @Slot(list, list)
    def save_orders(self, orders: list, deleted_orders: list) -> None:
        """Save orders in a single transaction."""
        try:
            # Build OrderInput list
            final_orders: list[OrderInput] = []
            for o in orders:
                products = []
                for p in o.get("products", []):
                    pi = OrderInput(
                        id=p.get("id", ""),
                        date="",
                        supplier="",
                        nfe_key="",
                        freight=0,
                        unloading=0,
                        products=[],
                    )
                    pi.name = p.get("name", "")
                    pi.quantity = p.get("quantity", 0)
                    pi.price = p.get("price", 0)
                    pi.total = p.get("total", 0)
                    pi.order_id = p.get("order_id", "")
                    pi.item_ordinal = p.get("itemOrdinal")
                    products.append(pi)
                oi = OrderInput(
                    id=o.get("id", ""),
                    date=o.get("date", ""),
                    supplier=o.get("supplier", ""),
                    nfe_key=o.get("nfeKey", ""),
                    freight=o.get("freight", 0),
                    unloading=o.get("unloading", 0),
                    products=products,
                )
                final_orders.append(oi)

            self._save_orders_fn(final_orders, deleted_orders)
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
            self._save_expenses_fn(expense_inputs, month)
            self.save_completed.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Business Logic ──────────────────────────────────────────────

    @Slot(object)
    def distribute_freight(self, order: dict[str, Any]) -> dict[str, Any]:
        """Distribute freight costs across products in an order."""
        try:
            order_input = OrderInput(
                id=order.get("id", ""),
                date=order.get("date", ""),
                supplier=order.get("supplier", ""),
                nfe_key=order.get("nfeKey", ""),
                freight=order.get("freight", 0),
                unloading=order.get("unloading", 0),
                products=[
                    OrderInput(
                        id=p.get("id", ""),
                        date="",
                        supplier="",
                        nfe_key="",
                        freight=0,
                        unloading=0,
                        products=[],
                    )
                    for p in order.get("products", [])
                ],
            )
            for i, p in enumerate(order.get("products", [])):
                order_input.products[i].name = p.get("name", "")
                order_input.products[i].quantity = p.get("quantity", 0)
                order_input.products[i].price = p.get("price", 0)
                order_input.products[i].total = p.get("total", 0)
                order_input.products[i].order_id = p.get("order_id", "")
                order_input.products[i].item_ordinal = p.get("itemOrdinal")

            result = self._freight.distribute(order_input)
            return {
                "order_id": result.order_id,
                "old_freight": result.old_freight,
                "old_unloading": result.old_unloading,
                "ratio": result.ratio,
                "products_total_before": result.products_total_before,
                "products_total_after": result.products_total_after,
                "new_products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "quantity": p.quantity,
                        "price": p.price,
                        "total": p.total,
                        "order_id": p.order_id,
                        "itemOrdinal": p.item_ordinal,
                    }
                    for p in result.new_products
                ],
            }
        except ValueError as exc:
            self.error_occurred.emit(str(exc))
            return {}

    @Slot(str)
    def import_xml(self, file_path: str) -> dict[str, Any]:
        """Import data from an NFe XML file."""
        try:
            result = self._xml_import.parse_file(file_path)
            return {
                "orders": [
                    {
                        "id": o.id,
                        "date": o.date,
                        "supplier": o.supplier,
                        "nfeKey": o.nfe_key,
                        "freight": o.freight,
                        "unloading": o.unloading,
                        "products": [
                            {
                                "id": p.id,
                                "name": p.name,
                                "quantity": p.quantity,
                                "price": p.price,
                                "total": p.total,
                                "order_id": p.order_id,
                                "itemOrdinal": p.item_ordinal,
                            }
                            for p in o.products
                        ],
                    }
                    for o in result.orders
                ],
                "warnings": result.warnings,
            }
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"orders": [], "warnings": []}

    @Slot(object)
    def validate_order(self, order: dict[str, Any]) -> dict[str, Any]:
        """Validate an order and return the result."""
        try:
            order_input = OrderInput(
                id=order.get("id", ""),
                date=order.get("date", ""),
                supplier=order.get("supplier", ""),
                nfe_key=order.get("nfeKey", ""),
                freight=order.get("freight", 0),
                unloading=order.get("unloading", 0),
                products=[
                    OrderInput(
                        id=p.get("id", ""),
                        date="",
                        supplier="",
                        nfe_key="",
                        freight=0,
                        unloading=0,
                        products=[],
                    )
                    for p in order.get("products", [])
                ],
            )
            for i, p in enumerate(order.get("products", [])):
                order_input.products[i].name = p.get("name", "")
                order_input.products[i].quantity = p.get("quantity", 0)
                order_input.products[i].price = p.get("price", 0)
                order_input.products[i].total = p.get("total", 0)
                order_input.products[i].order_id = p.get("order_id", "")
                order_input.products[i].item_ordinal = p.get("itemOrdinal")

            result = self._validation.validate_order(order_input)
            return {
                "valid": result.valid,
                "errors": result.errors,
            }
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return {"valid": False, "errors": [str(exc)]}

    @Slot(str, int)
    def validate_expense(self, description: str, value: int) -> dict[str, Any]:
        """Validate a single expense."""
        result = self._validation.validate_expense(description, value)
        return {
            "valid": result.valid,
            "errors": result.errors,
        }
