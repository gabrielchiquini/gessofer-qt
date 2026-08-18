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


def import_xml(file_path: str) -> XmlImportResult:
    """Module-level convenience function to import orders from an NFe XML file.

    Creates a BusinessService instance using the DI container and delegates
    to its ``import_xml`` method.

    Args:
        file_path: Path to the NFe XML file.

    Returns:
        XmlImportResult with parsed orders and any warnings.
    """
    from injector_module import get_injector

    injector = get_injector()
    service = injector.get(BusinessService)
    return service.import_xml(file_path)


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


class BusinessService:
    """Business logic service for order and expense operations."""

    def __init__(
        self,
        freight_service: FreightDistributionService,
        xml_service: XmlImportService,
        validation_service: ValidationService,
    ) -> None:
        self._freight_service = freight_service
        self._xml_service = xml_service
        self._validation_service = validation_service

    def distribute_freight(self, order: OrderInput) -> FreightResult:
        """Distribute freight/unloading costs across products in an order."""
        try:
            result = self._freight_service.distribute(order)
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

    def import_xml(self, file_path: str) -> XmlImportResult:
        """Import orders from an NFe XML file."""
        try:
            result = self._xml_service.parse_file(file_path)
            return xml_import_result_to_dict(result)
        except Exception as exc:
            logger.error("Error in import_xml: %s", exc)
            return XmlImportResult(orders=[], warnings=[])

    def validate_order(self, order: OrderInput) -> Validation:
        """Validate an order dict."""
        try:
            result = self._validation_service.validate_order(order)
            return Validation(valid=result.valid, errors=result.errors)
        except Exception as exc:
            logger.error("Error in validate_order: %s", exc)
            return Validation(valid=False, errors=[str(exc)])

    def validate_expense(self, description: str, value: int) -> Validation:
        """Validate an expense."""
        try:
            result = self._validation_service.validate_expense(description, value)
            return Validation(valid=result.valid, errors=result.errors)
        except Exception as exc:
            logger.error("Error in validate_expense: %s", exc)
            return Validation(valid=False, errors=[str(exc)])
