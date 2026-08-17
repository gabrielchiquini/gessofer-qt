from __future__ import annotations

import logging

from backend import OrderInput
from backend.services.freight_distribution import (
    FreightDistributionResult,
    FreightDistributionService,
)
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportResult as BackendXmlImportResult, XmlImportService
from models.order import FreightResult, Order, XmlImportResult
from models.output import Product
from models.validation import Validation

logger = logging.getLogger(__name__)


def freight_result_to_dict(result: FreightDistributionResult) -> FreightResult:
    """Transform a FreightDistributionResult into a FreightResult dataclass."""
    return FreightResult(
        order_id=result.order_id,
        old_freight=result.old_freight,
        old_unloading=result.old_unloading,
        ratio=result.ratio,
        products_total_before=result.products_total_before,
        products_total_after=result.products_total_after,
        new_products=[
            Product(
                id=p.id,
                name=p.name,
                quantity=p.quantity,
                price=p.price,
                total=p.total,
                order_id=p.order_id,
                item_ordinal=p.item_ordinal,
            )
            for p in result.new_products
        ],
    )


def xml_import_result_to_dict(result: BackendXmlImportResult) -> XmlImportResult:
    """Transform a BackendXmlImportResult into a XmlImportResult dataclass."""
    return XmlImportResult(
        orders=[
            Order(
                id=o.id,
                date=o.date,
                supplier=o.supplier,
                nfe_key=o.nfe_key,
                freight=o.freight,
                unloading=o.unloading,
                products=[
                    Product(
                        id=p.id,
                        name=p.name,
                        quantity=p.quantity,
                        price=p.price,
                        total=p.total,
                        order_id=p.order_id,
                        item_ordinal=p.item_ordinal,
                        warnings=getattr(p, "warnings", []),
                    )
                    for p in o.products
                ],
            )
            for o in result.orders
        ],
        warnings=result.warnings,
    )


def distribute_freight(order: OrderInput) -> FreightResult:
    """
    Distribute freight/unloading costs across products in an order.

    Args:
        order: Order dict with products.

    Returns:
        FreightResult dataclass with distribution result. On ValueError, returns empty result.
    """
    try:
        service = FreightDistributionService()
        result = service.distribute(order)
        return freight_result_to_dict(result)
    except ValueError:
        return FreightResult(
            order_id="",
            old_freight=0,
            old_unloading=0,
            ratio=0.0,
            products_total_before=0,
            products_total_after=0,
            new_products=[],
        )
    except Exception as exc:
        logger.error("Error in distribute_freight: %s", exc)
        return FreightResult(
            order_id="",
            old_freight=0,
            old_unloading=0,
            ratio=0.0,
            products_total_before=0,
            products_total_after=0,
            new_products=[],
        )


def import_xml(file_path: str) -> XmlImportResult:
    """
    Import orders from an NFe XML file.

    Args:
        file_path: Path to the XML file.

    Returns:
        XmlImportResult dataclass with orders and warnings. On error, returns empty result.
    """
    try:
        service = XmlImportService()
        result = service.parse_file(file_path)
        return xml_import_result_to_dict(result)
    except Exception as exc:
        logger.error("Error in import_xml: %s", exc)
        return XmlImportResult(orders=[], warnings=[])


def validate_order(order: OrderInput) -> Validation:
    """
    Validate an order dict.

    Args:
        order: Order dict to validate.

    Returns:
        Validation dataclass with valid and errors.
    """
    try:
        service = ValidationService()
        result = service.validate_order(order)
        return Validation(valid=result.valid, errors=result.errors)
    except Exception as exc:
        logger.error("Error in validate_order: %s", exc)
        return Validation(valid=False, errors=[str(exc)])


def validate_expense(description: str, value: int) -> Validation:
    """
    Validate an expense.

    Args:
        description: Expense description.
        value: Expense value in cents.

    Returns:
        Validation dataclass with valid and errors.
    """
    try:
        service = ValidationService()
        result = service.validate_expense(description, value)
        return Validation(valid=result.valid, errors=result.errors)
    except Exception as exc:
        logger.error("Error in validate_expense: %s", exc)
        return Validation(valid=False, errors=[str(exc)])
