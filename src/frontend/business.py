from __future__ import annotations

import logging
from typing import Any

from backend.qml.qml_business import QmlBusiness
from backend.qml.qml_fetch import QmlFetch
from backend.qml.qml_save import QmlSave
from backend.qml.qml_transformers import (
    dict_to_order_input,
    freight_result_to_dict,
    xml_import_result_to_dict,
)
from backend.services.freight_distribution import FreightDistributionService
from backend.services.validation_service import ValidationService
from backend.services.xml_import_service import XmlImportService

logger = logging.getLogger(__name__)


_business_handler: QmlBusiness | None = None


def _get_business_handler() -> QmlBusiness:
    """Lazy-initialize the BusinessHandler singleton."""
    global _business_handler
    if _business_handler is None:
        validation = ValidationService()
        freight = FreightDistributionService()
        xml_import = XmlImportService()
        fetch_service = QmlFetch()
        save_service = QmlSave()
        transformers = type("Transformers", (), {
            "transform_order_input": lambda s, d: dict_to_order_input(d),
            "transform_expense_input": lambda s, d: None,
        })()
        _business_handler = QmlBusiness(fetch_service, save_service, transformers)
    return _business_handler


def distribute_freight(order: dict[str, Any]) -> dict[str, Any]:
    """
    Distribute freight/unloading costs across products in an order.

    Args:
        order: Order dict with products.

    Returns:
        Dict with distribution result. On ValueError, returns {}.
    """
    try:
        from backend.qml.qml_transformers import dict_to_order_input
        from backend.services.freight_distribution import FreightDistributionService

        order_input = dict_to_order_input(order)
        service = FreightDistributionService()
        result = service.distribute(order_input)
        return freight_result_to_dict(result)
    except ValueError:
        return {}
    except Exception as exc:
        logger.error("Error in distribute_freight: %s", exc)
        return {}


def import_xml(file_path: str) -> dict[str, Any]:
    """
    Import orders from an NFe XML file.

    Args:
        file_path: Path to the XML file.

    Returns:
        Dict with 'orders' and 'warnings' keys. On error, returns empty result.
    """
    try:
        from backend.services.xml_import_service import XmlImportService
        from backend.qml.qml_transformers import xml_import_result_to_dict

        service = XmlImportService()
        result = service.parse_file(file_path)
        return xml_import_result_to_dict(result)
    except Exception as exc:
        logger.error("Error in import_xml: %s", exc)
        return {"orders": [], "warnings": []}


def validate_order(order: dict[str, Any]) -> dict[str, Any]:
    """
    Validate an order dict.

    Args:
        order: Order dict to validate.

    Returns:
        Dict with 'valid' (bool) and 'errors' (list[str]) keys.
    """
    try:
        from backend.qml.qml_transformers import dict_to_order_input
        from backend.services.validation_service import ValidationService

        order_input = dict_to_order_input(order)
        service = ValidationService()
        result = service.validate_order(order_input)
        return {"valid": result.valid, "errors": result.errors}
    except Exception as exc:
        logger.error("Error in validate_order: %s", exc)
        return {"valid": False, "errors": [str(exc)]}


def validate_expense(description: str, value: int) -> dict[str, Any]:
    """
    Validate an expense.

    Args:
        description: Expense description.
        value: Expense value in cents.

    Returns:
        Dict with 'valid' (bool) and 'errors' (list[str]) keys.
    """
    try:
        from backend.services.validation_service import ValidationService

        service = ValidationService()
        result = service.validate_expense(description, value)
        return {"valid": result.valid, "errors": result.errors}
    except Exception as exc:
        logger.error("Error in validate_expense: %s", exc)
        return {"valid": False, "errors": [str(exc)]}
