from .database.connection import get_engine, discover_database_path
from .injector_module import InjectorModule, get_injector
from .entities.orm import Order, Product, Expense
from .models.dto import OrderInput, ProductInput, ExpenseInput, PageResponse
from .repositories.order_repository import OrderRepository
from .repositories.expense_repository import ExpenseRepository
from .utils.currency import cents_to_display, parse_currency_to_cents
from .utils.date import (
    parse_month_for_orders,
    parse_month_for_expenses,
    br_date_to_iso,
    iso_to_br_date,
    current_month_orders,
    current_month_expenses,
    format_time_now,
)
from .utils.text import normalize_text

# Errors
from .errors import BackendError, ValidationError, DatabaseError, XmlParseError

# Services
from .services.save_order_service import SaveOrderService, SaveExpenseService
from .services.freight_distribution import FreightDistributionService
from .services.xml_import_service import XmlImportService
from .services.validation_service import ValidationService

# API
from .api.orders import orders_for_month, product_list
from .api.save_orders import save_orders
from .api.save_expenses import expenses_for_month, save_expenses

__all__ = [
    # Database
    "get_engine",
    "discover_database_path",
    # Injector
    "InjectorModule",
    "get_injector",
    # Entities
    "Order",
    "Product",
    "Expense",
    # DTOs
    "OrderInput",
    "ProductInput",
    "ExpenseInput",
    "PageResponse",
    # Repositories
    "OrderRepository",
    "ExpenseRepository",
    # Utils
    "cents_to_display",
    "parse_currency_to_cents",
    "parse_month_for_orders",
    "parse_month_for_expenses",
    "br_date_to_iso",
    "iso_to_br_date",
    "current_month_orders",
    "current_month_expenses",
    "format_time_now",
    "normalize_text",
    # Errors
    "BackendError",
    "ValidationError",
    "DatabaseError",
    "XmlParseError",
    # Services
    "SaveOrderService",
    "SaveExpenseService",
    "FreightDistributionService",
    "XmlImportService",
    "ValidationService",
    # API
    "orders_for_month",
    "product_list",
    "save_orders",
    "expenses_for_month",
    "save_expenses",
]
