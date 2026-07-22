from __future__ import annotations

import logging
from typing import cast

from backend import OrderInput
from backend.services.freight_distribution import (
    FreightDistributionResult,
    FreightDistributionService,
)
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportResult, XmlImportService
from bridge.models.order import FreightResultDict, XmlImportResultDict
from bridge.models.validation import ValidationDict

logger = logging.getLogger(__name__)


def freight_result_to_dict(result: FreightDistributionResult) -> FreightResultDict:
    """Transform a FreightDistributionResult into a bridge-compatible dict."""
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


def xml_import_result_to_dict(result: XmlImportResult) -> XmlImportResultDict:
    """Transform an XmlImportResult into a bridge-compatible dict."""
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


def distribute_freight(order: OrderInput) -> FreightResultDict:
    """
    Distribute freight/unloading costs across products in an order.

    Args:
        order: Order dict with products.

    Returns:
        Dict with distribution result. On ValueError, returns {}.
    """
    try:
        service = FreightDistributionService()
        result = service.distribute(order)
        return freight_result_to_dict(result)
    except ValueError:
        return cast(FreightResultDict, {})
    except Exception as exc:
        logger.error("Error in distribute_freight: %s", exc)
        return cast(FreightResultDict, {})


def import_xml(file_path: str) -> XmlImportResultDict:
    """
    Import orders from an NFe XML file.

    Args:
        file_path: Path to the XML file.

    Returns:
        Dict with 'orders' and 'warnings' keys. On error, returns empty result.
    """
    try:
        service = XmlImportService()
        result = service.parse_file(file_path)
        return xml_import_result_to_dict(result)
    except Exception as exc:
        logger.error("Error in import_xml: %s", exc)
        return {"orders": [], "warnings": []}


def validate_order(order: OrderInput) -> ValidationDict:
    """
    Validate an order dict.

    Args:
        order: Order dict to validate.

    Returns:
        Dict with 'valid' (bool) and 'errors' (list[str]) keys.
    """
    try:
        service = ValidationService()
        result = service.validate_order(order)
        return {"valid": result.valid, "errors": result.errors}
    except Exception as exc:
        logger.error("Error in validate_order: %s", exc)
        return {"valid": False, "errors": [str(exc)]}


def validate_expense(description: str, value: int) -> ValidationDict:
    """
    Validate an expense.

    Args:
        description: Expense description.
        value: Expense value in cents.

    Returns:
        Dict with 'valid' (bool) and 'errors' (list[str]) keys.
    """
    try:
        service = ValidationService()
        result = service.validate_expense(description, value)
        return {"valid": result.valid, "errors": result.errors}
    except Exception as exc:
        logger.error("Error in validate_expense: %s", exc)
        return {"valid": False, "errors": [str(exc)]}
