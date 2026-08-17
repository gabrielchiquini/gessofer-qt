from .database.connection import get_engine, discover_database_path
from .injector_module import InjectorModule, get_injector
from .entities.orm import Order, Product, Expense
from models.input import OrderInput, ProductInput, ExpenseInput
from models.output import PageResponse
from .repositories.order_repository import OrderRepository
from .repositories.expense_repository import ExpenseRepository

# Utils
from .utils.backup import (
    classify_backup,
    compute_retention_decision,
    discover_backup_dir,
    get_backup_path,
    parse_backup_filename,
)
from .utils.currency import cents_to_display, parse_currency_to_cents
from .utils.date import (
    parse_month_for_orders,
    parse_month_for_expenses,
    br_date_to_iso,
    iso_to_br_date,
    current_month_orders,
    format_time_now,
)
from .utils.text import normalize_text

# Errors
from .errors import BackendError, ValidationError, DatabaseError, XmlParseError, BackupError

# Services
from .services.backup_service import BackupService
from .services.save_order_service import SaveOrderService, SaveExpenseService
from .services.freight_distribution import FreightDistributionService
from .services.xml_import_service import XmlImportService
from .services.validation_service import ValidationService

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
    "classify_backup",
    "compute_retention_decision",
    "discover_backup_dir",
    "get_backup_path",
    "parse_backup_filename",
    "cents_to_display",
    "parse_currency_to_cents",
    "parse_month_for_orders",
    "parse_month_for_expenses",
    "br_date_to_iso",
    "iso_to_br_date",
    "current_month_orders",
    "format_time_now",
    "normalize_text",
    # Errors
    "BackendError",
    "ValidationError",
    "DatabaseError",
    "XmlParseError",
    "BackupError",
    # Services
    "BackupService",
    "SaveOrderService",
    "SaveExpenseService",
    "FreightDistributionService",
    "XmlImportService",
    "ValidationService",
]
